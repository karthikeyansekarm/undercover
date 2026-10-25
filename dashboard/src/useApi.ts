import { useCallback, useEffect, useState } from "react";
import { get } from "./api";

export interface ApiState<T> {
  data: T | null;
  error: string | null;
  reload: () => void;
}

// Loads `path`, then loads it again every `intervalMs` while `pollWhile` holds.
export function useApi<T>(
  path: string,
  pollWhile?: (data: T) => boolean,
  intervalMs = 1000,
): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const reload = useCallback(() => {
    setVersion((v) => v + 1);
  }, []);

  useEffect(() => {
    let live = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const load = () => {
      get<T>(path)
        .then((value) => {
          if (!live) return;
          setData(value);
          setError(null);
          if (pollWhile?.(value)) timer = setTimeout(load, intervalMs);
        })
        .catch((e: unknown) => {
          if (live) setError(String(e));
        });
    };
    load();
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [path, pollWhile, intervalMs, version]);

  return { data, error, reload };
}
