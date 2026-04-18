interface Props {
  url: string | null | undefined;
  name: string;
  size?: number;
  grayscale?: boolean;
  className?: string;
}

export function ChampionPortrait({
  url,
  name,
  size = 64,
  grayscale = false,
  className = "",
}: Props) {
  if (!url) {
    return (
      <div
        style={{ width: size, height: size }}
        className={`flex items-center justify-center bg-surface-2 font-bold uppercase text-faint ${className}`}
      >
        {name.slice(0, 2)}
      </div>
    );
  }
  return (
    <img
      src={url}
      alt={name}
      loading="lazy"
      width={size}
      height={size}
      className={`block ${grayscale ? "grayscale" : ""} ${className}`}
    />
  );
}
