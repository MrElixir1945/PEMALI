"use client";

import { useState, useEffect, useRef } from "react";
import NavBar from "@/components/NavBar";
import Footer from "@/components/Footer";
import { Send, Terminal as TerminalIcon, Globe, Shield, User, Bot, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface Memory {
  id: number;
  role: string;
  content: string;
  name?: string;
}

interface AuditLog {
  id: number;
  location: string;
  issue: string;
  narrative: string;
  thk: string;
}

export default function DashboardPage() {
  const [prompt, setPrompt] = useState("");
  const [memories, setMemories] = useState<Memory[]>([]);
  const [auditLog, setAuditLog] = useState<AuditLog | null>(null);
  const [satelliteImg, setSatelliteImg] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [renderedIds, setRenderedIds] = useState<Set<number>>(new Set());
  
  const logEndRef = useRef<HTMLDivElement>(null);

  const fetchSession = async () => {
    try {
      const res = await fetch("/api/session");
      const data = await res.json();
      if (!data.session_id) return;

      if (sessionId !== data.session_id) {
        setSessionId(data.session_id);
        setMemories([]);
        setRenderedIds(new Set());
        setAuditLog(null);
        setSatelliteImg(null);
      }

      setMemories(data.memories);
      setAuditLog(data.audit_log);
      setSatelliteImg(data.satellite_img);
    } catch (e) {
      console.error("Fetch error", e);
    }
  };

  useEffect(() => {
    fetchSession();
    const interval = setInterval(fetchSession, 2000);
    return () => clearInterval(interval);
  }, [sessionId]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [memories]);

  const handleSend = async () => {
    if (!prompt.trim()) return;
    setIsTyping(true);
    const p = prompt;
    setPrompt("");

    try {
      await fetch("/api/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: p }),
      });
    } catch (e) {
      console.error("Trigger error", e);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-[#FAF9F6]">
      <NavBar />
      <main className="flex-1 flex max-w-7xl mx-auto w-full h-[calc(100vh-140px)] overflow-hidden">
        {/* Left Panel - Context (simplified for Next.js version) */}
        <div className="w-1/3 border-r border-stone-200 p-8 hidden lg:flex flex-col bg-stone-50/50">
          <h2 className="text-xs font-semibold uppercase text-stone-400 tracking-widest mb-6">System Heartbeat</h2>
          <div className="space-y-4">
             <div className="flex items-center text-sm gap-3">
               <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]"></div>
               <span className="text-stone-700 font-medium">Communicate Layer Online</span>
             </div>
             <div className="flex items-center text-sm gap-3">
               <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]"></div>
               <span className="text-stone-700 font-medium">Worker Node Active</span>
             </div>
          </div>

          {satelliteImg && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-12"
            >
              <h2 className="text-xs font-semibold uppercase text-stone-400 tracking-widest mb-4">Latest Evidence</h2>
              <div className="rounded-xl overflow-hidden border border-stone-200 shadow-sm">
                <img src={satelliteImg} alt="Satellite" className="w-full h-48 object-cover" />
              </div>
            </motion.div>
          )}

          {auditLog && (
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-8 bg-white border border-stone-200 p-5 rounded-2xl shadow-sm"
            >
               <div className="flex items-center gap-2 mb-3">
                 <Shield className="w-4 h-4 text-stone-400" />
                 <span className="text-xs font-bold text-stone-500 uppercase tracking-tighter">Audit Result</span>
               </div>
               <div className="text-sm font-semibold text-stone-800 mb-1">{auditLog.location}</div>
               <div className="text-xs text-red-600 font-medium mb-3">{auditLog.issue}</div>
               <div className="text-[10px] bg-stone-100 text-stone-600 px-2 py-1 rounded-full inline-block font-bold">
                 {auditLog.thk}
               </div>
            </motion.div>
          )}
        </div>

        {/* Right Panel - Chat Area */}
        <div className="flex-1 flex flex-col relative bg-white lg:bg-transparent">
          <div className="flex-1 overflow-y-auto px-6 py-10 lg:px-12 space-y-6">
            <AnimatePresence>
              {memories.length === 0 && (
                <motion.div 
                  initial={{ opacity: 0 }} 
                  animate={{ opacity: 1 }} 
                  className="h-full flex flex-col items-center justify-center text-center opacity-40"
                >
                  <Bot className="w-12 h-12 mb-4 text-stone-300" />
                  <p className="text-sm font-light text-stone-500">Siap melakukan audit ekologi otonom.<br />Silakan masukkan instruksi di bawah.</p>
                </motion.div>
              )}
              {memories.map((mem) => {
                if (mem.role === "system") return null;
                const isUser = mem.role === "user";
                const isTool = mem.role === "tool";

                return (
                  <motion.div
                    key={mem.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                  >
                    {isTool ? (
                      <div className="ml-8 pl-4 border-l border-stone-200 py-1 max-w-xl">
                        <div className="flex items-center gap-2 mb-1">
                          <TerminalIcon className="w-3 h-3 text-stone-300" />
                          <span className="text-[10px] font-mono text-stone-400 uppercase tracking-widest">{mem.name}</span>
                        </div>
                        <div className="text-[11px] text-stone-500 font-mono italic">
                          {JSON.parse(mem.content).agent_hint || "Executing tool cycle..."}
                        </div>
                      </div>
                    ) : (
                      <div className={`max-w-[80%] px-6 py-4 rounded-3xl ${
                        isUser 
                          ? "bg-stone-900 text-white rounded-tr-sm" 
                          : "bg-white border border-stone-200 text-stone-800 rounded-tl-sm shadow-sm"
                      } text-sm leading-relaxed`}>
                        {mem.content}
                      </div>
                    )}
                  </motion.div>
                );
              })}
            </AnimatePresence>
            {isTyping && (
              <div className="flex justify-start">
                 <div className="bg-white border border-stone-200 px-6 py-4 rounded-3xl rounded-tl-sm shadow-sm">
                    <Loader2 className="w-4 h-4 text-stone-300 animate-spin" />
                 </div>
              </div>
            )}
            <div ref={logEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-6 bg-gradient-to-t from-[#FAF9F6] via-[#FAF9F6] to-transparent">
             <div className="max-w-2xl mx-auto relative">
               <input 
                 type="text" 
                 value={prompt}
                 onChange={(e) => setPrompt(e.target.value)}
                 onKeyDown={(e) => e.key === "Enter" && handleSend()}
                 placeholder="Instruksikan audit..."
                 className="w-full bg-white border border-stone-200 rounded-full py-4 pl-8 pr-16 text-sm focus:outline-none focus:ring-1 focus:ring-stone-300 shadow-sm"
               />
               <button 
                 onClick={handleSend}
                 className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-stone-900 text-white rounded-full hover:bg-black transition-colors"
               >
                 <Send className="w-4 h-4" />
               </button>
             </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
