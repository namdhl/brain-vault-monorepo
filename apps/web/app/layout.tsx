import "./globals.css";
import { RegisterServiceWorker } from "@/components/register-sw";
import { Nav } from "@/components/nav";

export const metadata = {
  title: "Brain Vault",
  description: "Capture text, links and media into a Markdown-based second brain."
};

export default function RootLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <RegisterServiceWorker />
        <Nav />
        {children}
      </body>
    </html>
  );
}
