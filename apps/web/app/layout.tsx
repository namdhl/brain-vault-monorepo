import "./globals.css";
import { RegisterServiceWorker } from "@/components/register-sw";

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
        {children}
      </body>
    </html>
  );
}
