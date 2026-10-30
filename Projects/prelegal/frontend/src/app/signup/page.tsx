import type { Metadata } from "next";
import Link from "next/link";
import { AuthLayout } from "@/auth/AuthLayout";
import { SignUpForm } from "@/auth/SignUpForm";

export const metadata: Metadata = {
  title: "Create account | prelegal",
};

export default function SignUpPage() {
  return (
    <AuthLayout
      title="Create your account"
      subtitle="Draft Common Paper agreements with an AI assistant and keep them in one place."
      footer={
        <>
          Already have an account?{" "}
          <Link href="/login" className="font-semibold text-[#209dd7] hover:text-[#032147]">
            Sign in
          </Link>
        </>
      }
    >
      <SignUpForm />
    </AuthLayout>
  );
}
