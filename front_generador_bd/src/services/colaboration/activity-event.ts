export type ActivityEvent = {
  id: number;
  room: string;
  actor: number | null;
  actor_name: string;
  actor_kind: string;
  type: string;
  target_id: string;
  summary: string;
  data: Record<string, unknown>;
  created_at: string;
};
