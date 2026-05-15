import { cn } from "@/lib/utils";

interface IconProps {
  name: string;
  className?: string;
}

export default function Icon({ name, className }: IconProps) {
  return (
    <img
      src={`/icons/${name}.svg`}
      alt=""
      className={cn("w-5 h-5", className)}
      aria-hidden="true"
    />
  );
}
