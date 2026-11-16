"use client";

import { useRef, type ReactNode } from "react";

type BentoCardProps = {
  children: ReactNode;
  className?: string;
};

export default function BentoCard({ children, className = "" }: BentoCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);

  function handleMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    cardRef.current.style.setProperty("--mouse-x", `${x}px`);
    cardRef.current.style.setProperty("--mouse-y", `${y}px`);
  }

  return (
    <div
      ref={cardRef}
      onMouseMove={handleMouseMove}
      className={`bento-card ${className}`}
    >
      <div className="bento-spotlight" aria-hidden="true" />
      {children}
    </div>
  );
}
