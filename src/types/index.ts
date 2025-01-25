export interface Channel {
  id: string;
  username: string;
  title: string;
  memberCount: number;
  category: string;
  ownerId: string;
  isPromoted: boolean;
  promotionExpiresAt?: Date;
  approved: boolean;
  createdAt: Date;
}

export interface User {
  id: string;
  username?: string;
  isBanned: boolean;
  channelCount: number;
  createdAt: Date;
}

export interface PromotionPlan {
  id: string;
  name: string;
  price: number;
  durationDays: number;
  position: 'top' | 'featured';
}

export interface Config {
  minMembers: number;
  memberTiers: number[];
  maxChannelsPerUser: number;
  promotionDuration: number;
  broadcastTimes: string[];
  pinnedLinks: string[];
}