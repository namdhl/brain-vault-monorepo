"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Capture" },
  { href: "/items", label: "Items" },
  { href: "/jobs", label: "Jobs" },
  { href: "/search", label: "Search" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="nav">
      <span className="nav-brand">Brain Vault</span>
      <div className="nav-links">
        {links.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={pathname === href ? "nav-link active" : "nav-link"}
          >
            {label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
