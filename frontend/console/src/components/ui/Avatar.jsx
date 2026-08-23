import { cn } from "@/lib/cn";
/** Deterministic hue per person, so the same user is always the same colour. */
function hueFor(seed) {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) % 360;
  }
  return hash;
}
export function initialsOf(fullName) {
  const parts = fullName.split(" ").filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}
export function Avatar({ name, size = "md", className }) {
  const hue = hueFor(name);
  const dims = { sm: "size-6 text-[10px]", md: "size-8 text-xs", lg: "size-10 text-sm" }[size];
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full font-bold text-white select-none",
        dims,
        className,
      )}
      style={{ backgroundColor: `hsl(${hue} 55% 42%)` }}
      title={name}
      aria-hidden
    >
      {initialsOf(name)}
    </span>
  );
}
