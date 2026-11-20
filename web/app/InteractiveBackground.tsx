"use client";

import { useEffect, useRef } from "react";

export default function InteractiveBackground() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let targetX = window.innerWidth / 2;
    let targetY = 240;
    let currentX = targetX;
    let currentY = targetY;
    let rafId: number;
    let isHovering = false;

    // Respecter la préférence de réduction de mouvement
    const mediaQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mediaQuery.matches) {
      container.style.setProperty("--cursor-x", `${targetX}px`);
      container.style.setProperty("--cursor-y", `${targetY}px`);
      container.style.setProperty("--cursor-opacity", "0.4");
      return;
    }

    const onPointerMove = (e: PointerEvent) => {
      targetX = e.clientX;
      targetY = e.clientY;
      if (!isHovering) {
        isHovering = true;
        container.style.setProperty("--cursor-opacity", "1");
      }
    };

    const onPointerLeave = () => {
      isHovering = false;
      container.style.setProperty("--cursor-opacity", "0.35");
    };

    window.addEventListener("pointermove", onPointerMove, { passive: true });
    document.documentElement.addEventListener("pointerleave", onPointerLeave);

    const tick = () => {
      // Interpolation fluide (lerp) pour un suivi soyeux du curseur
      const ease = 0.09;
      currentX += (targetX - currentX) * ease;
      currentY += (targetY - currentY) * ease;

      container.style.setProperty("--cursor-x", `${currentX.toFixed(1)}px`);
      container.style.setProperty("--cursor-y", `${currentY.toFixed(1)}px`);

      rafId = requestAnimationFrame(tick);
    };

    rafId = requestAnimationFrame(tick);

    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      document.documentElement.removeEventListener("pointerleave", onPointerLeave);
      cancelAnimationFrame(rafId);
    };
  }, []);

  return (
    <div ref={containerRef} className="interactive-bg" aria-hidden="true">
      {/* Halos ambiants qui flottent doucement */}
      <div className="ambient-orb ambient-orb-1" />
      <div className="ambient-orb ambient-orb-2" />

      {/* Halo lumineux qui suit le curseur */}
      <div className="cursor-spotlight" />

      {/* Grille géométrique qui s'illumine sous le curseur */}
      <div className="cursor-grid" />
    </div>
  );
}
