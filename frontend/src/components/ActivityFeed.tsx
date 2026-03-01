import React from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';
import {
  CircleStackIcon,
  MagnifyingGlassCircleIcon,
  UserCircleIcon,
  BoltIcon,
} from '@heroicons/react/24/outline';
import { formatDistanceToNow } from 'date-fns';

interface ActivityItem {
  id: string;
  type: 'store' | 'recall' | 'profile' | 'connect';
  message: string;
  time: Date;
}

const iconMap = {
  store: CircleStackIcon,
  recall: MagnifyingGlassCircleIcon,
  profile: UserCircleIcon,
  connect: BoltIcon,
};

const colorMap = {
  store: 'text-cyan-400 bg-cyan-400/10',
  recall: 'text-amber-400 bg-amber-500/10',
  profile: 'text-purple-400 bg-purple-500/10',
  connect: 'text-green-400 bg-green-500/10',
};

interface ActivityFeedProps {
  items: ActivityItem[];
}

const ActivityFeed: React.FC<ActivityFeedProps> = ({ items }) => {
  if (items.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-gray-600">
        No recent activity. Start by storing a memory.
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {items.map((item, i) => {
        const Icon = iconMap[item.type];
        return (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-black/[0.03] transition-colors"
          >
            <div className={clsx('p-1.5 rounded-lg', colorMap[item.type])}>
              <Icon className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-700 truncate">{item.message}</p>
            </div>
            <span className="text-[11px] text-gray-400 whitespace-nowrap">
              {formatDistanceToNow(item.time, { addSuffix: true })}
            </span>
          </motion.div>
        );
      })}
    </div>
  );
};

export default ActivityFeed;
export type { ActivityItem };
