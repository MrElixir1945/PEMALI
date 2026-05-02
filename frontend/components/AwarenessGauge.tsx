"use client";

import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

interface AwarenessGaugeProps {
  score: number;
}

export default function AwarenessGauge({ score }: AwarenessGaugeProps) {
  const data = [
    { name: 'Aware', value: score },
    { name: 'Unaware', value: 100 - score }
  ];

  const getColor = (value: number) => {
    if (value < 30) return '#ef4444'; // red
    if (value < 60) return '#eab308'; // yellow
    return '#3b82f6'; // blue
  };

  const color = getColor(score);

  return (
    <div className="relative h-[250px] w-full flex items-center justify-center flex-col">
      <div className="h-[200px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="100%"
              startAngle={180}
              endAngle={0}
              innerRadius={80}
              outerRadius={100}
              paddingAngle={0}
              dataKey="value"
              stroke="none"
              cornerRadius={5}
            >
              <Cell fill={color} />
              <Cell fill="#f1f5f9" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="absolute bottom-6 flex flex-col items-center">
        <span className="text-4xl font-black" style={{ color }}>{score}</span>
        <span className="text-xs uppercase font-bold text-slate-400 mt-1">/ 100 Score</span>
      </div>
    </div>
  );
}
