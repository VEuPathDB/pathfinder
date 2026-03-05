import type { Strategy } from "@pathfinder/shared";

export type ConversationKind = "strategy";

export interface ConversationItem {
  id: string;
  kind: ConversationKind;
  title: string;
  updatedAt: string;
  siteId?: string;
  stepCount?: number;
  strategyItem?: Strategy;
}
