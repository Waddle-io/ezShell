import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { getWebSessionUser } from "@/lib/auth";

export default async function AdminLayout({ children }: { children: React.ReactNode }) {
  const h = await headers();
  const user = await getWebSessionUser(h.get("cookie"));

  if (!user || user.role !== "admin") {
    redirect("/dashboard");
  }

  return <>{children}</>;
}
