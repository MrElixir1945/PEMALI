import { JetBrains_Mono } from "next/font/google";

const mono = JetBrains_Mono({ subsets: ["latin"] });

interface CodeBlockProps {
  code: string;
  filename?: string;
}

export default function CodeBlock({ code, filename }: CodeBlockProps) {
  return (
    <div className="bg-white border border-stone-200 rounded-xl overflow-hidden shadow-sm my-6">
      {filename && (
        <div className="bg-stone-50 border-b border-stone-200 px-4 py-2 flex justify-between items-center">
          <span className="text-[10px] font-mono text-stone-500 uppercase tracking-widest">{filename}</span>
          <div className="flex space-x-1.5">
            <div className="w-2 h-2 rounded-full bg-stone-200"></div>
            <div className="w-2 h-2 rounded-full bg-stone-200"></div>
            <div className="w-2 h-2 rounded-full bg-stone-200"></div>
          </div>
        </div>
      )}
      <div className="p-6 overflow-x-auto">
        <pre className={`${mono.className} text-xs text-stone-700 leading-relaxed`}>
          <code>{code}</code>
        </pre>
      </div>
    </div>
  );
}
