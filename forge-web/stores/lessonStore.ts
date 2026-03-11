import { createEntityStore, withCreateLoading } from "./factory";
import { lessons as lessonsApi } from "@/lib/api";
import type { Lesson, LessonCreate } from "@/lib/types";

export const useLessonStore = createEntityStore<Lesson>({
  listFn: (s) => lessonsApi.list(s),
  responseKey: "lessons",
  getItemId: (item) => item.id,
  wsEvents: {
    "lesson.created": { op: "create" },
  },
});

export async function createLesson(slug: string, data: LessonCreate[]): Promise<string[]> {
  return withCreateLoading(useLessonStore, () => lessonsApi.create(slug, data));
}
