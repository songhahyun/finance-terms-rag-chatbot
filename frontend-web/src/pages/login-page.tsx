import { useState, type FormEvent } from "react";
import { EyeOff, Lock, User } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/app/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function LoginPage(): JSX.Element {
  const { login, signup } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [role, setRole] = useState<"user" | "admin">("user");
  const [isSignup, setIsSignup] = useState(false);
  const [rememberId, setRememberId] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const redirectTo = (location.state as { from?: string } | null)?.from ?? "/chat";

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      if (isSignup) {
        await signup({ username, password, role });
      } else {
        await login({ username, password });
      }
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "로그인에 실패했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f3f6fb] p-4 md:p-6">
      <div className="mx-auto grid min-h-[calc(100vh-2rem)] max-w-[1280px] overflow-hidden rounded-2xl border border-[#dbe2ea] bg-white md:grid-cols-2">
        <section className="flex flex-col justify-between p-8 md:p-12">
          <div>
            <div className="mb-16">
              <p className="text-3xl font-extrabold text-[#1e5eff]">FinRAG Chatbot</p>
              <p className="mt-2 text-sm text-[#7b889b]">금융 지식을 가장 빠르고 정확하게</p>
            </div>

            <h1 className="text-5xl font-extrabold tracking-tight text-[#0f172a]">{isSignup ? "회원가입" : "로그인"}</h1>
            <p className="mt-3 text-sm font-medium text-[#97a3b4]">FinRAG Chatbot에 오신 것을 환영합니다.</p>

            <form className="mt-8 space-y-4" onSubmit={onSubmit}>
              <div className="relative">
                <User className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9aa6b6]" />
                <Input
                  className="h-12 rounded-lg border-[#dce3ec] pl-11"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="아이디를 입력하세요"
                  required
                />
              </div>
              <div className="relative">
                <Lock className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9aa6b6]" />
                <Input
                  type="password"
                  className="h-12 rounded-lg border-[#dce3ec] pl-11 pr-11"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="비밀번호를 입력하세요"
                  required
                />
                <EyeOff className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9aa6b6]" />
              </div>

              {isSignup && (
                <select
                  className="h-12 w-full rounded-lg border border-[#dce3ec] bg-white px-3 text-sm"
                  value={role}
                  onChange={(e) => setRole(e.target.value as "user" | "admin")}
                >
                  <option value="user">General User</option>
                  <option value="admin">Admin</option>
                </select>
              )}

              {error && <p className="text-sm text-[#ef4444]">{error}</p>}

              <Button type="submit" disabled={isLoading} className="h-12 w-full rounded-lg bg-[#2162ff] text-base font-bold hover:bg-[#1e56e8]">
                {isLoading ? "처리 중..." : isSignup ? "가입하기" : "로그인"}
              </Button>
            </form>

            <div className="mt-4 flex items-center justify-between text-sm text-[#7b889b]">
              <label className="inline-flex items-center gap-2">
                <input type="checkbox" checked={rememberId} onChange={(e) => setRememberId(e.target.checked)} className="h-4 w-4 rounded border-[#d0d8e4]" />
                아이디 기억하기
              </label>
              <button type="button" className="font-semibold text-[#3567ff]">비밀번호 찾기</button>
            </div>

            <div className="mt-5 text-sm text-[#7b889b]">
              {isSignup ? "이미 계정이 있나요?" : "처음이신가요?"}{" "}
              <Link to="#" onClick={() => setIsSignup((prev) => !prev)} className="font-semibold text-[#3567ff]">
                {isSignup ? "로그인" : "회원가입"}
              </Link>
            </div>
          </div>

          <p className="text-xs text-[#a0acbc]">© 2026 FinRAG Chatbot. All rights reserved.</p>
        </section>

        <section className="hidden bg-[linear-gradient(180deg,#f7faff_0%,#f2f6fd_100%)] p-8 md:flex md:items-center md:justify-center">
          <img
            src="/assets/bank_icon.png"
            alt="Bank illustration"
            className="h-auto w-full max-w-[480px] object-contain"
          />
        </section>
      </div>
    </div>
  );
}
