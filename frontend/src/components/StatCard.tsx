import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface StatCardProps {
  label: string;
  value: number;
  icon: React.ElementType;
  trend?: { value: number; up: boolean };
  color?: 'cyan' | 'amber' | 'green' | 'purple';
  delay?: number;
}

const colorMap = {
  cyan: {
    bg: 'bg-cyan-400/10',
    text: 'text-cyan-400',
    border: 'border-cyan-400/20',
    glow: 'shadow-glow-cyan',
  },
  amber: {
    bg: 'bg-amber-500/10',
    text: 'text-amber-400',
    border: 'border-amber-500/20',
    glow: 'shadow-glow-amber',
  },
  green: {
    bg: 'bg-green-500/10',
    text: 'text-green-400',
    border: 'border-green-500/20',
    glow: '',
  },
  purple: {
    bg: 'bg-purple-500/10',
    text: 'text-purple-400',
    border: 'border-purple-500/20',
    glow: '',
  },
};

const StatCard: React.FC<StatCardProps> = ({ label, value, icon: Icon, trend, color = 'cyan', delay = 0 }) => {
  const [displayValue, setDisplayValue] = useState(0);
  const c = colorMap[color];

  useEffect(() => {
    if (value === 0) return;
    const duration = 1000;
    const steps = 30;
    const increment = value / steps;
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= value) {
        current = value;
        clearInterval(timer);
      }
      setDisplayValue(Math.round(current));
    }, duration / steps);
    return () => clearInterval(timer);
  }, [value]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      className={clsx('glass-card p-5 flex items-start justify-between', c.glow)}
    >
      <div>
        <p className="text-sm font-medium text-gray-500 mb-1">{label}</p>
        <p className={clsx('text-3xl font-bold', c.text)}>{displayValue.toLocaleString()}</p>
        {trend && (
          <p className={clsx('text-xs mt-1 font-medium', trend.up ? 'text-green-400' : 'text-red-400')}>
            {trend.up ? '+' : '-'}{trend.value}% from last week
          </p>
        )}
      </div>
      <div className={clsx('p-3 rounded-xl', c.bg, c.border, 'border')}>
        <Icon className={clsx('w-6 h-6', c.text)} />
      </div>
    </motion.div>
  );
};

export default StatCard;
