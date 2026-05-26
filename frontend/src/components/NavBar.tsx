"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";

export default function NavBar() {
  const pathname = usePathname();

  const links = [
    { name: "Platform", href: "/" },
    { name: "Monitor", href: "/monitor" },
    { name: "Laporan", href: "/laporan" },
    { name: "Methodology", href: "/methodology" },
    { name: "Engineering", href: "/engineering" },
  ];

  return (
    <div className="w-full border-b border-[var(--pemali-border)]">
      <nav className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto w-full">
        <div className="flex items-center flex-1">
          <Link href="/" className="flex items-center gap-2">
            <Image src="/images/logo.png" alt="PEMALI" width={32} height={32} className="object-contain" />
            <span className="font-serif text-2xl font-semibold tracking-tight" style={{ color: "var(--pemali-text-primary)" }}>Pemali.</span>
          </Link>
        </div>
        <div className="hidden md:flex space-x-12 relative flex-none justify-center">
          {links.map((link) => (
            <Link
              key={link.name}
              href={link.href}
              className={`text-sm transition-colors relative py-1 ${
                pathname === link.href ? "font-medium" : ""
              }`}
              style={{
                color: pathname === link.href ? "var(--pemali-text-primary)" : "var(--pemali-text-muted)",
              }}
            >
              {link.name}
              {pathname === link.href && (
                <motion.div
                  layoutId="nav-indicator"
                  className="absolute bottom-0 left-0 w-full h-[1px]"
                  style={{ backgroundColor: "var(--pemali-text-primary)" }}
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
            </Link>
          ))}
        </div>
        <div className="flex-1 hidden md:flex justify-end items-center">
          <Link
            href="/agentic"
            className="mr-3 flex items-center justify-center px-4 py-2 rounded-xl text-xs font-medium transition-all hover:bg-[#D4D2C7]"
            style={{ backgroundColor: "#E5E3DB", color: "#2C2C2A", border: "1px solid rgba(44, 44, 42, 0.1)" }}
          >
            Enter Agentic &rarr;
          </Link>
          <Link
            href="/dashboard"
            className="flex items-center justify-center px-4 py-2 rounded-xl text-xs font-medium transition-all hover:bg-[#444441]"
            style={{ backgroundColor: "#2C2C2A", color: "#fff" }}
          >
            Enter Dashboard &rarr;
          </Link>
        </div>
      </nav>
    </div>
  );
}
