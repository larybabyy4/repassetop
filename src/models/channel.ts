import mongoose from 'mongoose';
import { Channel } from '../types';

const channelSchema = new mongoose.Schema<Channel>({
  id: { type: String, required: true, unique: true },
  username: { type: String, required: true },
  title: { type: String, required: true },
  memberCount: { type: Number, required: true },
  category: { type: String, required: true },
  ownerId: { type: String, required: true },
  isPromoted: { type: Boolean, default: false },
  promotionExpiresAt: { type: Date },
  approved: { type: Boolean, default: false },
  createdAt: { type: Date, default: Date.now }
});

export const ChannelModel = mongoose.model<Channel>('Channel', channelSchema);