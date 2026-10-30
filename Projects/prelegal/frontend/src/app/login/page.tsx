import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { AuthLayout } from "@/auth/AuthLayout";
import { SignInForm } from "@/auth/SignInForm";

export const metadata: Metadata = {
  title: "Sign in | prelegal",
};

export default function LoginPage() {
  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to draft agreements and open your saved documents."
      footer={
        <>
          New to Prelegal?{" "}
          <Link href="/signup" className="font-semibold text-[#209dd7] hover:text-[#032147]">
            Create an account
          </Link>
        </>
      }
    >
      {/* The form reads ?registered and ?email, which are only known in the browser. */}
      <Suspense>
        <SignInForm />
      </Suspense>
    </AuthLayout>
  );
}
