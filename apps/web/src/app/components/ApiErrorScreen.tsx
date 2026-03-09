import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/lib/components/ui/Button";

interface ApiErrorScreenProps {
  error: string;
  onRetry: () => void;
}

export function ApiErrorScreen({ error, onRetry }: ApiErrorScreenProps) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 bg-background text-foreground">
      <AlertTriangle className="h-10 w-10 text-destructive" />
      <div className="text-center">
        <p className="text-sm font-medium">Unable to connect to the API</p>
        <p className="mt-1 max-w-sm text-xs text-muted-foreground">{error}</p>
      </div>
      <Button variant="outline" size="sm" onClick={onRetry}>
        <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
        Retry
      </Button>
    </div>
  );
}
