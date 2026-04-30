import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Bot, ChevronDown, FileText, LayoutDashboard, LogOut, MessageSquare, Plus, Settings } from "lucide-react";
import { useAuth } from "@/app/auth-context";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const RECENT_CHATS = [
  "ELS 상품 설명해줘",
  "신용등급 하락 원인",
  "금리 인상 영향 분석",
  "회사채 투자 리스크",
  "환율 전망 알려줘",
];

export function AppShell(): JSX.Element {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const isAdmin = Boolean(user?.roles.includes("admin"));

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen bg-[#f5f7fb] p-3 md:p-5">
      <div className="mx-auto min-h-[calc(100vh-1.5rem)] max-w-[1400px] overflow-hidden rounded-2xl border border-[#dbe2ea] bg-white">
        <header className="flex h-14 items-center justify-between border-b border-[#e6ebf1] px-5">
          <Link to="/chat" className="flex items-center gap-2 text-[28px] font-extrabold tracking-tight text-[#1e5eff]">
            <Bot className="h-5 w-5" />
            <span className="text-xl">FinRAG Chatbot</span>
          </Link>
          <div className="flex items-center gap-3 text-sm font-semibold text-[#4f5f78]">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-[#e9eef6] text-[#64748b]">유</span>
            <span>{user?.username} 님</span>
            <ChevronDown className="h-4 w-4" />
            <Button variant="ghost" size="sm" onClick={handleLogout} className="ml-1 text-[#4f5f78]">
              <LogOut className="mr-1 h-4 w-4" /> 로그아웃
            </Button>
          </div>
        </header>

        <div className="grid min-h-[calc(100vh-5.5rem)] grid-cols-1 md:grid-cols-[220px_1fr]">
          <aside className="border-r border-[#e6ebf1] bg-[#fbfcff] p-4">
            <Button className="mb-4 h-11 w-full bg-[#2162ff] text-white hover:bg-[#1e56e8]">
              <Plus className="mr-2 h-4 w-4" /> 새 대화
            </Button>

            <nav className="space-y-1">
              <NavItem to="/chat" label="대화" icon={<MessageSquare className="h-4 w-4" />} isActive={location.pathname.startsWith("/chat")} />
              {isAdmin && (
                <NavItem
                  to="/admin"
                  label="대시보드"
                  icon={<LayoutDashboard className="h-4 w-4" />}
                  isActive={location.pathname.startsWith("/admin")}
                />
              )}
              <FakeItem label="지식 문서" icon={<FileText className="h-4 w-4" />} />
              <FakeItem label="설정" icon={<Settings className="h-4 w-4" />} />
            </nav>

            <div className="mt-6 border-t border-[#e6ebf1] pt-4">
              <p className="mb-2 text-xs font-bold text-[#7b889b]">최근 대화</p>
              <div className="space-y-1">
                {RECENT_CHATS.map((item, idx) => (
                  <button
                    key={`${item}-${idx}`}
                    type="button"
                    className={cn(
                      "w-full rounded-md px-2 py-2 text-left text-sm text-[#4f5f78] hover:bg-[#eef3ff]",
                      idx === 0 && location.pathname.startsWith("/chat") && "bg-[#eef3ff] text-[#1e5eff]",
                    )}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          </aside>

          <main className="bg-white p-4 md:p-5">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}

function NavItem({ to, label, icon, isActive }: { to: string; label: string; icon: JSX.Element; isActive: boolean }): JSX.Element {
  return (
    <NavLink
      to={to}
      className={cn(
        "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold",
        isActive ? "bg-[#e9f1ff] text-[#1e5eff]" : "text-[#4f5f78] hover:bg-[#f0f4fb]",
      )}
    >
      {icon}
      <span>{label}</span>
    </NavLink>
  );
}

function FakeItem({ label, icon }: { label: string; icon: JSX.Element }): JSX.Element {
  return (
    <button type="button" className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold text-[#4f5f78] hover:bg-[#f0f4fb]">
      {icon}
      <span>{label}</span>
    </button>
  );
}

