"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TransformWrapper, TransformComponent } from "react-zoom-pan-pinch";

import PemaliMascot from "./PemaliMascot";

export interface ReasoningStep {
  id: string;
  label: string;
  sublabel: string;
  icon: string;
  status: "pending" | "active" | "done";
}

interface ReasoningCanvasProps {
  steps: ReasoningStep[];
  isVisible: boolean;
  mascotState: "running" | "thinking" | "writing";
}

const DEFAULT_STEPS: ReasoningStep[] = [
  { id: "orchestrator", label: "PEMALI Orchestrator", sublabel: "Processing Instruction", icon: "🧠", status: "done" },
  { id: "data_processing", label: "Pengolahan Data", sublabel: "Context Preparation", icon: "⚙️", status: "active" },
  { id: "satellite", label: "Satellite Module", sublabel: "Sentinel-2 Acquisition", icon: "🛰", status: "pending" },
  { id: "osint", label: "OSINT Module", sublabel: "Intelligence Gathering", icon: "📡", status: "pending" },
  { id: "community", label: "Community Module", sublabel: "Social Engagement", icon: "👥", status: "pending" },
  { id: "reporting", label: "Reporting Module", sublabel: "THK Report Synthesis", icon: "📋", status: "pending" },
  { id: "final_output", label: "Output Laporan", sublabel: "Data Finalization", icon: "📑", status: "pending" },
];

function StatusDot({ status }: { status: ReasoningStep["status"] }) {
  if (status === "done") {
    return <span className="w-2 h-2 rounded-full bg-stone-300 inline-block" />;
  }
  if (status === "active") {
    return <span className="w-2 h-2 rounded-full bg-stone-900 inline-block animate-pulse" />;
  }
  return <span className="w-2 h-2 rounded-full border border-stone-200 inline-block" />;
}

function AnimatedLine({ active, height = 32 }: { active: boolean, height?: number }) {
  return (
    <div className="flex flex-col items-center" style={{ height }}>
      <svg width="1" height={height} viewBox={`0 0 1 ${height}`}>
        <line
          x1="0.5"
          y1="0"
          x2="0.5"
          y2={height}
          stroke={active ? "#1C1917" : "#E7E5E4"}
          strokeWidth="1"
          className="transition-colors duration-500"
        />
      </svg>
    </div>
  );
}

function NodeCard({ step, activeStepId, mascotState }: { step: ReasoningStep, activeStepId: string, mascotState: string }) {
  const isMascotHere = activeStepId === step.id;
  const isActive = step.status === "active";
  const isDone = step.status === "done";
  
  return (
    <div className="relative flex flex-col items-center w-full">
      <div
        className={`relative flex items-center gap-4 px-6 py-6 w-full transition-all duration-500 bg-white ${
          isActive
            ? "border-stone-900 shadow-[0_8px_30px_rgb(0,0,0,0.08)] z-20 scale-[1.02]"
            : isDone
            ? "border-stone-200/60 opacity-80"
            : "border-stone-100/40 opacity-30 grayscale"
        }`}
        style={{ borderWidth: isActive ? '1px' : '0.5px', borderStyle: 'solid' }}
      >
        <div className="flex items-center">
          <StatusDot status={step.status} />
        </div>
        <div className="flex-1 min-w-0 flex flex-col">
          <div className={`font-serif text-[17px] tracking-tight leading-tight ${isActive ? "text-stone-900 font-medium" : "text-stone-400"}`}>
            {step.label}
          </div>
          <div className="text-[9px] font-sans uppercase tracking-[0.2em] text-stone-300 mt-1.5 font-bold">
            {step.status === "active" ? "Processing..." : step.sublabel}
          </div>
        </div>

        {/* Mascot at the SIDE of the words */}
        <AnimatePresence>
          {isMascotHere && (
            <motion.div
              layoutId="mascot-avatar"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="absolute -right-12 top-1/2 -translate-y-1/2 z-50 pointer-events-none"
              transition={{ type: "spring", stiffness: 120, damping: 20 }}
            >
              <PemaliMascot state={mascotState as any} size={60} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default function ReasoningCanvas({ steps, isVisible, mascotState }: ReasoningCanvasProps) {
  const [displaySteps, setDisplaySteps] = useState<ReasoningStep[]>(
    steps.length > 0 ? steps : DEFAULT_STEPS
  );

  useEffect(() => {
    if (steps.length > 0) {
      setDisplaySteps(steps);
      return;
    }

    let current = 1;
    const timer = setInterval(() => {
      current++;
      setDisplaySteps((prev) =>
        prev.map((step, i) => {
          if (i < current) return { ...step, status: "done" };
          if (i === current) return { ...step, status: "active" };
          return step;
        })
      );
      if (current >= DEFAULT_STEPS.length - 1) clearInterval(timer);
    }, 2800);

    return () => clearInterval(timer);
  }, [steps]);

  const activeStep = displaySteps.find(s => s.status === "active") || displaySteps[displaySteps.length - 1];
  const activeStepId = activeStep?.id || "data_processing";

  const mainNode = displaySteps.find(s => s.id === "orchestrator") || DEFAULT_STEPS[0];
  const dataNode = displaySteps.find(s => s.id === "data_processing") || DEFAULT_STEPS[1];
  const outputNode = displaySteps.find(s => s.id === "final_output") || DEFAULT_STEPS[6];
  
  const subNodes = displaySteps.filter(s => !["orchestrator", "data_processing", "final_output"].includes(s.id));

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          key="reasoning-canvas"
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.98 }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }} 
          className="w-full h-full flex flex-col items-center justify-center relative overflow-hidden"
        >
          <TransformWrapper
            initialScale={1}
            minScale={0.5}
            maxScale={2}
            centerOnInit={true}
          >
            <TransformComponent wrapperStyle={{ width: '100%', height: '100%' }} contentStyle={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
              
              <div className="w-full h-full flex flex-col items-center justify-center px-8 py-20 min-h-[800px]">
                {/* Header */}
                <div className="mb-16 text-center">
                  <h2 className="font-serif text-3xl tracking-tight text-stone-900 mb-3">
                    Reasoning Protocol
                  </h2>
                  <div className="flex items-center justify-center gap-3">
                    <div className="h-[1px] w-8 bg-stone-200"></div>
                    <p className="text-stone-400 text-[10px] font-sans uppercase tracking-[0.3em] font-bold">
                      Autonomous Data Synthesis
                    </p>
                    <div className="h-[1px] w-8 bg-stone-200"></div>
                  </div>
                </div>

                {/* Main Layout Area */}
                <div className="flex w-full max-w-6xl justify-between items-start relative mt-4">
                  
                  {/* Orchestrator Column */}
                  <div className="flex flex-col items-center relative z-10 w-1/3 px-4">
                    <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="w-full relative">
                      <NodeCard step={mainNode} activeStepId={activeStepId} mascotState={mascotState} />
                      
                      {/* Horizontal line to Data Processing */}
                      <div className="absolute top-[36px] left-full w-full h-[1px] bg-stone-200 z-0">
                        <motion.div 
                          initial={{ scaleX: 0 }}
                          animate={{ scaleX: dataNode.status !== "pending" ? 1 : 0 }}
                          className="w-full h-full bg-stone-900 origin-left transition-transform duration-700"
                        />
                      </div>
                    </motion.div>
                    
                    {/* Vertical line down from Orchestrator */}
                    <AnimatedLine active={subNodes[0]?.status !== "pending"} height={40} />
                    
                    {/* List of Sub Modules */}
                    <div className="flex flex-col w-full border border-stone-200 divide-y divide-stone-100 bg-white">
                      {subNodes.map((step, i) => (
                        <motion.div
                          key={step.id}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          transition={{ delay: 0.1 + i * 0.05, duration: 0.4 }}
                          className="w-full"
                        >
                          <NodeCard step={step} activeStepId={activeStepId} mascotState={mascotState} />
                        </motion.div>
                      ))}
                    </div>
                  </div>

                  {/* Data Processing Column */}
                  <div className="flex flex-col items-center relative z-10 w-1/3 px-4">
                    <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="w-full relative">
                      <NodeCard step={dataNode} activeStepId={activeStepId} mascotState={mascotState} />
                      
                      {/* Horizontal line to Output */}
                      <div className="absolute top-[36px] left-full w-full h-[1px] bg-stone-200 z-0">
                        <motion.div 
                          initial={{ scaleX: 0 }}
                          animate={{ scaleX: outputNode.status !== "pending" ? 1 : 0 }}
                          className="w-full h-full bg-stone-900 origin-left transition-transform duration-700"
                        />
                      </div>
                    </motion.div>
                  </div>

                  {/* Output Column */}
                  <div className="flex flex-col items-center relative z-10 w-1/3 px-4">
                    <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="w-full">
                      <NodeCard step={outputNode} activeStepId={activeStepId} mascotState={mascotState} />
                    </motion.div>
                  </div>
                </div>
              </div>

            </TransformComponent>
          </TransformWrapper>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
