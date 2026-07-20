import {
  Show,
  SignInButton,
  SignUpButton,
  UserButton,
} from "@clerk/react";

export default function AuthControls() {
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
        <UserButton />
      </Show>
    </div>
  );
}
