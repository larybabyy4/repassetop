import mongoose from 'mongoose';
import { User } from '../types';

const userSchema = new mongoose.Schema<User>({
  id: { type: String, required: true, unique: true },
  username: { type: String },
  isBanned: { type: Boolean, default: false },
  channelCount: { type: Number, default: 0 },
  createdAt: { type: Date, default: Date.now }
});

export const UserModel = mongoose.model<User>('User', userSchema);