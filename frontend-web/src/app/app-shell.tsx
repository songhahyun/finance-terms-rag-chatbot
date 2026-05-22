import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Bot, FileText, LayoutDashboard, LogOut, MessageSquare, Plus, Settings } from "lucide-react";
import { useAuth } from "@/app/auth-context";
import { Button } from "@/components/ui/button";
import { CONVERSATIONS_CHANGED_EVENT, loadConversations, type Conversation } from "@/lib/conversations";
import { cn } from "@/lib/utils";

export function AppShell(): JSX.Element {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const isAdmin = Boolean(user?.roles.includes("admin"));
  const [recentConversations, setRecentConversations] = useState<Conversation[]>(() => loadConversations());

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const startNewConversation = () => {
    navigate("/chat");
  };

  useEffect(() => {
    const syncConversations = () => {
      setRecentConversations(loadConversations());
    };

    window.addEventListener("storage", syncConversations);
    window.addEventListener(CONVERSATIONS_CHANGED_EVENT, syncConversations);
    return () => {
      window.removeEventListener("storage", syncConversations);
      window.removeEventListener(CONVERSATIONS_CHANGED_EVENT, syncConversations);
    };
  }, []);

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
            <Button variant="ghost" size="sm" onClick={handleLogout} className="ml-1 text-[#4f5f78]">
              <LogOut className="mr-1 h-4 w-4" /> 로그아웃
            </Button>
          </div>
        </header>

        <div className="grid min-h-[calc(100vh-5.5rem)] grid-cols-1 md:grid-cols-[220px_1fr]">
          <aside className="border-r border-[#e6ebf1] bg-[#fbfcff] p-4">
            <Button className="mb-4 h-11 w-full bg-[#2162ff] text-white hover:bg-[#1e56e8]" onClick={startNewConversation}>
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
              <NavItem
                to="/knowledge-documents"
                label="지식 문서"
                icon={<FileText className="h-4 w-4" />}
                isActive={location.pathname.startsWith("/knowledge-documents")}
              />
              {isAdmin && <NavItem to="/settings" label="설정" icon={<Settings className="h-4 w-4" />} isActive={location.pathname.startsWith("/settings")} />}
            </nav>

            <div className="mt-6 border-t border-[#e6ebf1] pt-4">
              <p className="mb-2 text-xs font-bold text-[#7b889b]">최근 대화</p>
              <div className="space-y-1">
                {recentConversations.length > 0 ? (
                  recentConversations.slice(0, 10).map((conversation) => (
                    <button
                      key={conversation.id}
                      type="button"
                      className={cn(
                        "w-full truncate rounded-md px-2 py-2 text-left text-sm text-[#4f5f78] hover:bg-[#eef3ff]",
                        location.pathname.startsWith("/chat") &&
                          new URLSearchParams(location.search).get("conversationId") === conversation.id &&
                          "bg-[#eef3ff] text-[#1e5eff]",
                      )}
                      onClick={() => navigate(`/chat?conversationId=${encodeURIComponent(conversation.id)}`)}
                    >
                      {conversation.title}
                    </button>
                  ))
                ) : (
                  <p className="px-2 py-2 text-sm text-[#9aa6b6]">아직 최근 대화가 없습니다.</p>
                )}
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
