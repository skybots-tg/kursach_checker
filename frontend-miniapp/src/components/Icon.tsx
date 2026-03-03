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
  | "chevron-left";

interface IconProps extends React.SVGProps<SVGSVGElement> {
  name: IconName;
}

const paths: Record<IconName, string> = {
  home: "M3 11.5 12 4l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z",
  check: "M5 13l4 4L19 7",
  history: "M3 12a9 9 0 1 1 3 6.7M3 4v4h4M12 8v5l3 2",
  user: "M12 12a4 4 0 1 0-4-4 4 4 0 0 0 4 4zm0 2c-4.4 0-8 2-8 4.5V21h16v-2.5C20 16 16.4 14 12 14z",
  "file-text":
    "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M9 13h6M9 17h4M9 9h1",
  download:
    "M12 3v10m0 0 4-4m-4 4-4-4M5 19h14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1z",
  "credit-card":
    "M3 7a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zm0 3h18M7 15h3",
  settings:
    "M12 15.5A3.5 3.5 0 1 0 8.5 12 3.5 3.5 0 0 0 12 15.5zm7.4-3.1-.9-.5a1 1 0 0 1-.5-.9 1 1 0 0 1 .5-.9l.9-.5a1 1 0 0 0 .5-.9 8 8 0 0 0-.5-2 1 1 0 0 0-1.2-.6l-1 .3a1 1 0 0 1-1-.3l-.2-.3a1 1 0 0 1-.2-1.1l.4-1a1 1 0 0 0-.4-1 8 8 0 0 0-2-.5 1 1 0 0 0-.9.5l-.5.9a1 1 0 0 1-.9.5 1 1 0 0 1-.9-.5l-.5-.9a1 1 0 0 0-.9-.5 8 8 0 0 0-2 .5 1 1 0 0 0-.4 1l.4 1a1 1 0 0 1-.2 1.1l-.2.3a1 1 0 0 1-1 .3l-1-.3a1 1 0 0 0-1.2.6 8 8 0 0 0-.5 2 1 1 0 0 0 .5.9l.9.5a1 1 0 0 1 .5.9 1 1 0 0 1-.5.9l-.9.5a1 1 0 0 0-.5.9 8 8 0 0 0 .5 2 1 1 0 0 0 1.2.6l1-.3a1 1 0 0 1 1 .3l.2.3a1 1 0 0 1 .2 1.1l-.4 1a1 1 0 0 0 .4 1 8 8 0 0 0 2 .5 1 1 0 0 0 .9-.5l.5-.9a1 1 0 0 1 .9-.5 1 1 0 0 1 .9.5l.5.9a1 1 0 0 0 .9.5 8 8 0 0 0 2-.5 1 1 0 0 0 .4-1l-.4-1a1 1 0 0 1 .2-1.1l.2-.3a1 1 0 0 1 1-.3l1 .3a1 1 0 0 0 1.2-.6 8 8 0 0 0 .5-2 1 1 0 0 0-.5-.9z",
  "alert-triangle":
    "M10.29 3.86 2.82 17a2 2 0 0 0 1.71 3h14.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4m0 4h.01",
  "x-circle": "M12 21A9 9 0 1 0 3 12a9 9 0 0 0 9 9zm-4.2-11.8 8.4 8.4M8 17l8-8",
  "chevron-left": "M15 18l-6-6 6-6"
};

export const Icon: React.FC<IconProps> = ({ name, className, ...rest }) => {
  const d = paths[name];
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
      <path d={d} />
    </svg>
  );
};




