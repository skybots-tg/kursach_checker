import React from "react";

const icons: Record<string, JSX.Element> = {
  // Минимальный набор Lucide‑подобных иконок для админки
  layout: (
    <path
      d="M3 4h7v7H3zM14 4h7v4h-7zM14 11h7v9h-7zM3 13h7v7H3z"
      stroke="currentColor"
      strokeWidth="1.7"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),
  university: (
    <path
      d="M4 10v9h4v-6h4v6h4v-9M3 10h18L12 4 3 10z"
      stroke="currentColor"
      strokeWidth="1.7"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),
  book: (
    <path
      d="M6 4h11a2 2 0 0 1 2 2v11H8a2 2 0 0 0-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zM8 4v13"
      stroke="currentColor"
      strokeWidth="1.7"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),
  fileText: (
    <path
      d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6M10 13h8M10 17h5"
      stroke="currentColor"
      strokeWidth="1.7"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),
  sliders: (
    <path
      d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M4 14h4M12 12h4M20 16h4"
      stroke="currentColor"
      strokeWidth="1.7"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
      transform="translate(-2 -1)"
    />
  ),
  wand: (
    <path
      d="M4 20 20 4M15 4l5 5M4 9l5 5"
      stroke="currentColor"
      strokeWidth="1.7"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),
  creditCard: (
    <path
      d="M4 7h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2zM2 11h20M6 15h4"
      stroke="currentColor"
      strokeWidth="1.7"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),
  list: (
    <path
      d="M9 6h11M9 12h11M9 18h11M4 6h.01M4 12h.01M4 18h.01"
      stroke="currentColor"
      strokeWidth="1.7"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),
  users: (
    <path
      d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M18 8a4 4 0 1 1-8 0 4 4 0 0 1 8 0zM22 21v-2a4 4 0 0 0-3-3.87M18 4.13A4 4 0 0 1 20 8a4 4 0 0 1-1.33 3"
      stroke="currentColor"
      strokeWidth="1.7"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),
  messageSquare: (
    <path
      d="M21 15a2 2 0 0 1-2 2H8l-4 4V5a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2z"
      stroke="currentColor"
      strokeWidth="1.7"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),
  settings: (
    <path
      d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06A1.65 1.65 0 0 0 15 19.4a1.65 1.65 0 0 0-1 .6 1.65 1.65 0 0 0-.33 1.06V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-.33-1.06 1.65 1.65 0 0 0-1-.6 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-.6-1 1.65 1.65 0 0 0-1.06-.33H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.06-.33 1.65 1.65 0 0 0 .6-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-.6 1.65 1.65 0 0 0 .33-1.06V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 .33 1.06 1.65 1.65 0 0 0 1 .6 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 .6 1 1.65 1.65 0 0 0 1.06.33H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.06.33 1.65 1.65 0 0 0-.45.84z"
      stroke="currentColor"
      strokeWidth="1.5"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  ),
  log: (
    <path
      d="M8 4h11M8 8h11M8 12h7M4 4h.01M4 8h.01M4 12h.01M4 16h.01M8 16h11"
      stroke="currentColor"
      strokeWidth="1.7"
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  )
};

export interface IconProps {
  name: keyof typeof icons;
  className?: string;
}

export const Icon: React.FC<IconProps> = ({ name, className }) => {
  const path = icons[name];
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
      className={className}
    >
      {path}
    </svg>
  );
};


