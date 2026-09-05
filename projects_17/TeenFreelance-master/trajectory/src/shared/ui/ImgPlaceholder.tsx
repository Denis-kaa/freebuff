/**
 * ImgPlaceholder — React port of the prototype's placeholder system.
 * Bottom layer: generation prompt (always visible as fallback).
 * Top layer: <img> covering the prompt when src is provided.
 */
import { getImagePrompt } from '../mock/imagePrompts';

interface ImgPlaceholderProps {
  /** IMG-0X key from the registry. */
  imgId: string;
  /** Real image source; when absent the prompt layer stays visible. */
  src?: string;
  alt?: string;
  /** Inline height (px) — the container is width:100%. */
  height?: number;
}

export function ImgPlaceholder({ imgId, src, alt, height }: ImgPlaceholderProps) {
  const def = getImagePrompt(imgId);
  return (
    <div className="img-placeholder" style={height ? { height } : undefined} data-img-id={imgId}>
      {def && (
        <div className="ph-prompt">
          <span className="ph-tag">
            {def.id} · {def.label}
          </span>
          <span className="ph-text">{def.prompt}</span>
        </div>
      )}
      {src && <img src={src} alt={alt ?? imgId} />}
    </div>
  );
}
