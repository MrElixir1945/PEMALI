import { JetBrains_Mono } from "next/font/google";

const mono = JetBrains_Mono({ subsets: ["latin"] });

interface CodeBlockProps {
  code: string;
  filename?: string;
}

export default function CodeBlock({ code, filename }: CodeBlockProps) {
  return (
    <div className="rounded-xl overflow-hidden my-6 border" style={{ backgroundColor: "var(--pemali-bg)", borderColor: "var(--pemali-border)" }}>
      {filename && (
        <div className="border-b px-4 py-2 flex justify-between items-center" style={{ backgroundColor: "var(--pemali-surface)", borderColor: "var(--pemali-border)" }}>
          <span className="text-[10px] font-mono uppercase tracking-widest" style={{ color: "var(--pemali-text-muted)" }}>{filename}</span>
          <div className="flex space-x-1.5">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: "var(--pemali-border)" }}></div>
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: "var(--pemali-border)" }}></div>
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: "var(--pemali-border)" }}></div>
          </div>
        </div>
      )}
      <div className="p-6 overflow-x-auto">
        <pre className={`${mono.className} text-xs leading-relaxed`} style={{ color: "var(--pemali-text-secondary)" }}>
          <code>{code}</code>
        </pre>
      </div>
    </div>
  );
}
