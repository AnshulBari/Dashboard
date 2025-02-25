export default function DashboardLayout({
    children,
  }: Readonly<{
    children: React.ReactNode;
  }>) {
    return <div className="h-screen flex">
      {/* LEFT */}
      <div className="w-1/6 bg-yellow-200">l</div>
      {/* RIGHT */}
      <div className="w-5/6 bg-green-200">r</div>
    </div >;
  }