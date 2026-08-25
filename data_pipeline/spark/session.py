"""
Spark Session Configuration
===========================

Creates and configures PySpark sessions for the data pipeline.

Why Spark for this project:
- Cricsheet contains 200K+ deliveries across formats, growing over time
- Window functions for rolling averages and sequential analytics
- Parallel processing of ball-by-ball data
- DataFrame API provides clean, declarative ETL
- Scales to full dataset without code changes
- Memory-efficient with partitioning for large datasets
"""

from pyspark.sql import SparkSession
from pyspark.conf import SparkConf


def create_spark_session(
    app_name: str = "CricketIntelligence",
    master: str = "local[*]",
    driver_memory: str = "4g",
    enable_hive: bool = False,
) -> SparkSession:
    """
    Create a configured Spark session for the pipeline.
    
    Args:
        app_name: Name for the Spark application
        master: Spark master URL ('local[*]' for local, 'yarn' for cluster)
        driver_memory: Memory allocated to driver
        enable_hive: Enable Hive support for metastore
    
    Returns:
        Configured SparkSession
    """
    conf = SparkConf()
    conf.setAppName(app_name)
    conf.setMaster(master)
    
    # Memory configuration
    conf.set("spark.driver.memory", driver_memory)
    conf.set("spark.sql.shuffle.partitions", "8")
    conf.set("spark.default.parallelism", "8")
    
    # Enable Arrow for efficient Pandas UDFs
    conf.set("spark.sql.execution.arrow.pyspark.enabled", "true")
    
    # Adaptive query execution
    conf.set("spark.sql.adaptive.enabled", "true")
    
    # Broadcast threshold for joins (50MB)
    conf.set("spark.sql.autoBroadcastJoinThreshold", str(50 * 1024 * 1024))
    
    # Log level
    conf.set("spark.log.level", "WARN")
    
    builder = SparkSession.builder.config(conf=conf)
    
    if enable_hive:
        builder.enableHiveSupport()
    
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    
    return spark


def get_spark_session() -> SparkSession:
    """
    Get or create a singleton Spark session.
    Use this in pipeline scripts to avoid creating multiple sessions.
    """
    if not SparkSession._instantiatedSession:
        return create_spark_session()
    return SparkSession._instantiatedSession


def stop_spark_session():
    """Stop the active Spark session if one exists."""
    spark = get_spark_session()
    if spark is not None:
        spark.stop()
