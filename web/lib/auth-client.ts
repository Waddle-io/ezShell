"use client";

import { magicLinkClient } from "better-auth/client/plugins";
import { createAuthClient } from "better-auth/react";

/** Client Better Auth pour les pages (login, dashboard…). Parle à /api/auth/* sur la même origine. */
export const authClient = createAuthClient({
  plugins: [magicLinkClient()],
});
