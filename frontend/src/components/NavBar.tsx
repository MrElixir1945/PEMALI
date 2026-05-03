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
        <Link href="/" className="font-serif text-2xl font-semibold tracking-tight text-[#1C1917]">
          Pemali.
        </Link>
      </div>
      <div className="hidden md:flex space-x-12 relative">
        {links.map((link) => (
          <Link
            key={link.name}
            href={link.href}
            className={`text-sm transition-colors relative py-1 ${
              pathname === link.href ? "text-stone-900 font-medium" : "text-stone-500 hover:text-stone-900"
            }`}
          >
            {link.name}
            {pathname === link.href && (
              <motion.div
                layoutId="nav-indicator"
                className="absolute bottom-0 left-0 w-full h-[1px] bg-stone-900"
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
              />
            )}
          </Link>
        ))}
      </div>
      <div>
        <Link
          href="/dashboard"
          className="bg-stone-900 text-[#FAF9F6] px-5 py-2.5 rounded-sm text-sm font-medium hover:bg-stone-800 transition-all shadow-sm inline-block"
        >
          Enter Dashboard
        </Link>
      </div>
    </nav>
  );
}
