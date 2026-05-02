"use client";

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

interface NDVIChartProps {
  data: any[];
  baseline: number;
}

export default function NDVIChart({ data, baseline }: NDVIChartProps) {
  return (
    <div className="h-[300px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 20, right: 30, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
          <XAxis 
            dataKey="month" 
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#64748b', fontSize: 12 }}
            dy={10}
          />
          <YAxis 
            domain={['dataMin - 0.05', 'dataMax + 0.05']}
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#64748b', fontSize: 12 }}
            dx={-10}
          />
          <Tooltip 
            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
            labelStyle={{ fontWeight: 'bold', color: '#0f172a' }}
          />
          <ReferenceLine 
            y={baseline} 
            label={{ position: 'top', value: 'Baseline', fill: '#94a3b8', fontSize: 12 }}
            stroke="#94a3b8" 
            strokeDasharray="3 3" 
          />
          <Line 
            type="monotone" 
            dataKey="ndvi" 
            stroke="#059669" 
            strokeWidth={3}
            dot={{ r: 4, strokeWidth: 2, fill: '#fff' }}
            activeDot={{ r: 6, strokeWidth: 0, fill: '#059669' }}
            name="Nilai NDVI"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
