"use client";

import { motion, AnimatePresence } from "framer-motion";

export type MascotState = "idle" | "running" | "thinking" | "writing" | "done";

interface PemaliMascotProps {
  state: MascotState;
  size?: number;
}

export default function PemaliMascot({ state, size = 160 }: PemaliMascotProps) {
  // Map state to image filename
  const getImage = () => {
    switch (state) {
      case "idle": return "/penguin_standby_paper.png";
      case "running": return "/penguin_running_paper.png";
      case "thinking": return "/penguin_thinking_paper.png";
      case "writing": return "/penguin_writing_paper.png";
      case "done": return "/penguin_happy_paper.png";
      default: return "/penguin_standby_paper.png";
    }
  };

  return (
    <div
      className="relative flex items-center justify-center select-none"
      style={{ width: size, height: size }}
    >
      <AnimatePresence mode="wait">
        <motion.img
          key={state}
          src={getImage()}
          alt={`Mascot state: ${state}`}
          initial={{ opacity: 0, scale: 0.95, y: 10 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: -10 }}
          transition={{ duration: 0.3 }}
          className="object-contain"
          style={{ width: size, height: size }}
        />
      </AnimatePresence>
    </div>
  );
}
