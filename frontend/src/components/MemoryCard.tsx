import React from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import { ClockIcon, HashtagIcon, LinkIcon } from '@heroicons/react/24/outline';
import { formatDistanceToNow } from 'date-fns';

interface MemoryCardProps {
  id: string;
  text: string;
  metadata?: Record<string, any>;
  timestamp?: string;
  score?: number;
  index?: number;
  onClick?: () => void;
}

const MemoryCard: React.FC<MemoryCardProps> = ({ id, text, metadata, timestamp, score, index = 0, onClick }) => {
  const shortId = id.length > 12 ? `${id.slice(0, 6)}...${id.slice(-4)}` : id;
  const timeAgo = timestamp
    ? formatDistanceToNow(new Date(timestamp), { addSuffix: true })
    : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
      onClick={onClick}
      className={clsx(
        'glass-card p-4 transition-all duration-200 group',
        onClick && 'cursor-pointer'
      )}
    >
      {/* Header row */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <HashtagIcon className="w-3.5 h-3.5 text-gray-600" />
          <span className="text-xs font-mono text-gray-500">{shortId}</span>
        </div>
        <div className="flex items-center gap-2">
          {score !== undefined && (
            <span className="badge-cyan text-[10px]">
              {(score * 100).toFixed(0)}% match
            </span>
          )}
          {timeAgo && (
            <span className="flex items-center gap-1 text-[11px] text-gray-600">
              <ClockIcon className="w-3 h-3" />
              {timeAgo}
            </span>
          )}
        </div>
      </div>

      {/* Text */}
      <p className="text-sm text-gray-300 leading-relaxed line-clamp-3 group-hover:text-gray-200 transition-colors">
        {text}
      </p>

      {/* Metadata tags */}
      {metadata && Object.keys(metadata).length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {Object.entries(metadata).slice(0, 4).map(([key, val]) => (
            <span key={key} className="badge bg-space-700/60 text-gray-500 border border-space-600/30">
              <LinkIcon className="w-2.5 h-2.5 mr-1" />
              {key}: {String(val).slice(0, 20)}
            </span>
          ))}
        </div>
      )}
    </motion.div>
  );
};

export default MemoryCard;
