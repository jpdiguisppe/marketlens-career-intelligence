import { useEffect, useState } from "react";
import {
  Show,
  SignInButton,
  SignUpButton,
  UserButton,
  useAuth,
} from "@clerk/react";

import { getCurrentUser } from "./api";

type BackendAuthStatus = "idle" | "checking" | "verified" | "error";

export default function AuthControls() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [backendAuthStatus, setBackendAuthStatus] =
    useState<BackendAuthStatus>("idle");

  useEffect(() => {
    let cancelled = false;

    if (!isLoaded || !isSignedIn) {
      setBackendAuthStatus("idle");
      return () => {
        cancelled = true;
      };
    }

    async function verifyBackendSession() {
      setBackendAuthStatus("checking");

      try {
        const token = await getToken();

        if (!token) {
          throw new Error("Clerk did not provide a session token.");
        }

        const currentUser = await getCurrentUser(token);

        if (
          currentUser.auth_provider !== "clerk" ||
          !currentUser.user_id.startsWith("user_")
        ) {
          throw new Error("Backend returned an unexpected identity.");
        }

        if (!cancelled) {
          setBackendAuthStatus("verified");
        }
      } catch {
        if (!cancelled) {
          setBackendAuthStatus("error");
        }
      }
    }

    void verifyBackendSession();

    return () => {
      cancelled = true;
    };
  }, [getToken, isLoaded, isSignedIn]);

  const backendStatusText =
    backendAuthStatus === "verified"
      ? "Backend verified"
      : backendAuthStatus === "error"
        ? "Backend unavailable"
        : "Checking backend…";

  return (
    <div className="marketlens-auth-controls">
      <Show when="signed-out">
        <SignInButton mode="modal">
          <button className="marketlens-auth-button secondary" type="button">
            Sign in
          </button>
        </SignInButton>

        <SignUpButton mode="modal">
          <button className="marketlens-auth-button primary" type="button">
            Create account
          </button>
        </SignUpButton>
      </Show>

      <Show when="signed-in">
        <span
          className={`marketlens-auth-status ${backendAuthStatus}`}
          aria-live="polite"
        >
          {backendStatusText}
        </span>
        <UserButton />
      </Show>
    </div>
  );
}
