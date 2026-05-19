"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";

export default function NavBar() {
  const pathname = usePathname();

  const links = [
    { name: "Platform", href: "/" },
    { name: "Methodology", href: "/methodology" },
    { name: "Engineering", href: "/engineering" },
  ];

  return (
    <nav className="flex items-center justify-between px-8 py-6 max-w-7xl mx-auto w-full">
      <div className="flex items-center">
        <Link href="/" className="font-serif text-2xl font-semibold tracking-tight" style={{ color: "var(--pemali-text-primary)" }}>
          Pemali.
        </Link>
      </div>
      <div className="hidden md:flex space-x-12 relative">
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
      <div>
        <Link
          href="/dashboard"
          className="px-6 py-2.5 rounded-full text-sm font-medium transition-all inline-block"
          style={{
            backgroundColor: "var(--pemali-text-primary)",
            color: "var(--pemali-bg)",
          }}
        >
          Enter Dashboard
        </Link>
      </div>
    </nav>
  );
}
