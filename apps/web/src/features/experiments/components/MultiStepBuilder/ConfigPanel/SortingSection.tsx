import type { RecordAttribute } from "../../../api/crud";
import { ArrowUpDown } from "lucide-react";
import { Checkbox } from "@/lib/components/ui/Checkbox";
import { Label } from "@/lib/components/ui/Label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/lib/components/ui/Select";

export interface SortingSectionProps {
  sortAttribute: string | null;
  onSortAttributeChange: (v: string | null) => void;
  sortDirection: "ASC" | "DESC";
  onSortDirectionChange: (v: "ASC" | "DESC") => void;
  sortableAttributes: RecordAttribute[];
}

export function SortingSection({
  sortAttribute,
  onSortAttributeChange,
  sortDirection,
  onSortDirectionChange,
  sortableAttributes,
}: SortingSectionProps) {
  return (
    <div className="space-y-2">
      <Label className="flex items-center gap-2 text-xs font-normal text-foreground">
        <Checkbox
          checked={sortAttribute !== null}
          onCheckedChange={(checked) => {
            if (checked) {
              const suggested = sortableAttributes.find((a) => a.isSuggested);
              onSortAttributeChange(
                suggested?.name ?? sortableAttributes[0]?.name ?? null,
              );
            } else {
              onSortAttributeChange(null);
            }
          }}
          className="h-3.5 w-3.5"
        />
        <ArrowUpDown className="h-3 w-3" />
        Enable result ranking
      </Label>
      <p className="pl-5 text-[10px] text-muted-foreground">
        Rank results by a numeric attribute to compute Top-K metrics (P@K, R@K, E@K).
      </p>
      {sortAttribute !== null && (
        <div className="space-y-2 rounded-md border border-border bg-muted/30 p-3">
          <div>
            <Label className="mb-1.5 block text-[10px] text-muted-foreground">
              Sort attribute
            </Label>
            <Select value={sortAttribute} onValueChange={onSortAttributeChange}>
              <SelectTrigger className="h-8 text-xs">
                <SelectValue placeholder="Select attribute" />
              </SelectTrigger>
              <SelectContent>
                {sortableAttributes.length === 0 && (
                  <SelectItem value="" disabled>
                    No sortable attributes found
                  </SelectItem>
                )}
                {sortableAttributes.map((a) => (
                  <SelectItem key={a.name} value={a.name}>
                    {a.displayName}
                    {a.isSuggested ? " (suggested)" : ""}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="mb-1.5 block text-[10px] text-muted-foreground">
              Direction
            </Label>
            <div className="flex gap-2">
              {(["ASC", "DESC"] as const).map((dir) => (
                <button
                  key={dir}
                  type="button"
                  onClick={() => onSortDirectionChange(dir)}
                  className={`rounded-md border px-3 py-1 text-xs font-medium transition ${
                    sortDirection === dir
                      ? "border-primary bg-primary/10 text-primary"
                      : "border-border bg-card text-muted-foreground hover:border-primary/40"
                  }`}
                >
                  {dir === "ASC" ? "Ascending" : "Descending"}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
