import React from "react";

type IconName =
  | "home"
  | "check"
  | "history"
  | "user"
  | "file-text"
  | "download"
  | "credit-card"
  | "settings"
  | "alert-triangle"
  | "x-circle"
  | "chevron-left"
  | "chevron-right"
  | "sparkles"
  | "shield-check"
  | "zap"
  | "file-search"
  | "play"
  | "arrow-right"
  | "graduation-cap"
  | "clock";

interface IconProps extends React.SVGProps<SVGSVGElement> {
  name: IconName;
}

const paths: Record<IconName, string[]> = {
  home: ["M3 11.5 12 4l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"],
  check: ["M5 13l4 4L19 7"],
  history: ["M3 12a9 9 0 1 1 3 6.7", "M3 4v4h4", "M12 8v5l3 2"],
  user: [
    "M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4z",
    "M12 14c-4.4 0-8 2-8 4.5V21h16v-2.5C20 16 16.4 14 12 14z",
  ],
  "file-text": [
    "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z",
    "M14 2v6h6",
    "M9 13h6",
    "M9 17h4",
    "M9 9h1",
  ],
  download: [
    "M12 3v10m0 0 4-4m-4 4-4-4",
    "M5 19h14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1z",
  ],
  "credit-card": [
    "M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
    "M3 10h18",
    "M7 15h3",
  ],
  settings: [
    "M12 15.5A3.5 3.5 0 1 0 8.5 12 3.5 3.5 0 0 0 12 15.5z",
  ],
  "alert-triangle": [
    "M10.29 3.86 2.82 17a2 2 0 0 0 1.71 3h14.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z",
    "M12 9v4",
    "M12 17h.01",
  ],
  "x-circle": [
    "M12 21A9 9 0 1 0 3 12a9 9 0 0 0 9 9z",
    "M15 9l-6 6",
    "M9 9l6 6",
  ],
  "chevron-left": ["M15 18l-6-6 6-6"],
  "chevron-right": ["M9 18l6-6-6-6"],
  sparkles: [
    "M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.582a.5.5 0 0 1 0 .963L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z",
    "M20 3v4",
    "M22 5h-4",
  ],
  "shield-check": [
    "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
    "M9 12l2 2 4-4",
  ],
  zap: ["M13 2 3 14h9l-1 8 10-12h-9l1-8z"],
  "file-search": [
    "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z",
    "M14 2v6h6",
    "M11.5 14.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z",
    "M13.3 13.3 15 15",
  ],
  play: ["M5 3l14 9-14 9V3z"],
  "arrow-right": ["M5 12h14", "M12 5l7 7-7 7"],
  "graduation-cap": [
    "M22 10 12 5 2 10l10 5 10-5z",
    "M6 12v5c0 1 3 3 6 3s6-2 6-3v-5",
    "M22 10v6",
  ],
  clock: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z", "M12 7v5l3 3"],
};

export const Icon: React.FC<IconProps> = ({ name, className, ...rest }) => {
  const ds = paths[name] || [];
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      {...rest}
    >
      {ds.map((d, i) => (
        <path key={i} d={d} />
      ))}
    </svg>
  );
};
