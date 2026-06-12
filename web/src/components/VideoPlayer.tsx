import {
  type ComponentProps,
  type CSSProperties,
  forwardRef,
  isValidElement,
  type ReactNode,
  useEffect,
  useRef,
} from 'react';
import {
  CaptionsOffIcon,
  CaptionsOnIcon,
  CastEnterIcon,
  CastExitIcon,
  CheckIcon,
  ChevronIcon,
  FullscreenEnterIcon,
  FullscreenExitIcon,
  PauseIcon,
  PipEnterIcon,
  PipExitIcon,
  PlayIcon,
  RestartIcon,
  SeekIcon,
  SpinnerIcon,
  VolumeHighIcon,
  VolumeLowIcon,
  VolumeOffIcon,
} from '@videojs/react/icons';
import {
  BufferingIndicator,
  CaptionsButton,
  CastButton,
  Container,
  Controls,
  createPlayer,
  ErrorDialog,
  FullscreenButton,
  Gesture,
  Hotkey,
  Menu,
  MuteButton,
  PiPButton,
  PlayButton,
  PlaybackRateMenu,
  usePlaybackRateMenu,
  Popover,
  Poster,
  SeekButton,
  SeekIndicator,
  selectError,
  Slider,
  StatusAnnouncer,
  StatusIndicator,
  Time,
  TimeSlider,
  Tooltip,
  usePlayer,
  VolumeIndicator,
  VolumeSlider,
  type RenderProp,
} from '@videojs/react';
import { HlsVideo } from '@videojs/react/media/hls-video';
import { Video, videoFeatures } from '@videojs/react/video';
import './player.css';

const SEEK_TIME = 10;

const Player = createPlayer({ features: videoFeatures });

function isHlsUrl(url: string): boolean {
  const lower = url.toLowerCase();
  return lower.includes('.m3u8') || lower.includes('mpegurl');
}

const TOP_STATUS_ACTIONS = ['toggleSubtitles', 'toggleFullscreen', 'togglePictureInPicture'] as const;
const CENTER_STATUS_ACTIONS = ['togglePaused'] as const;

function PlaybackRateMenuItems(): ReactNode {
  const { options, setValue, value } = usePlaybackRateMenu();

  return (
    <Menu.RadioGroup className="media-menu__group" value={value} onValueChange={setValue} label="Playback rate">
      {options.map((option) => (
        <Menu.RadioItem key={option.value} className="media-menu__item" value={option.value} disabled={option.disabled}>
          <span>{option.label}</span>
          <Menu.ItemIndicator checked={option.value === value} forceMount className="media-menu__indicator">
            <CheckIcon className="media-icon" />
          </Menu.ItemIndicator>
        </Menu.RadioItem>
      ))}
    </Menu.RadioGroup>
  );
}

function PlaybackCallbacks({
  onError,
  onPlaying,
}: {
  onError?: (message: string) => void;
  onPlaying?: () => void;
}) {
  const errorState = usePlayer(selectError);
  const paused = Boolean(usePlayer((s) => s.paused));
  const wasPaused = useRef(true);
  const callbacksRef = useRef({ onError, onPlaying });
  callbacksRef.current = { onError, onPlaying };

  useEffect(() => {
    const message = errorState?.error?.message;
    if (message) {
      callbacksRef.current.onError?.(message);
    }
  }, [errorState?.error]);

  useEffect(() => {
    if (wasPaused.current && !paused) {
      callbacksRef.current.onPlaying?.();
    }
    wasPaused.current = paused;
  }, [paused]);

  return null;
}

interface MediaSkinPlayerProps {
  src: string;
  className?: string;
  poster?: string | RenderProp<Poster.State>;
  style?: CSSProperties;
  onError?: (message: string) => void;
  onPlaying?: () => void;
}

function MediaSkinPlayer({ src, className, poster, onError, onPlaying, ...rest }: MediaSkinPlayerProps) {
  return (
    <Player.Provider key={src}>
      <PlaybackCallbacks onError={onError} onPlaying={onPlaying} />
      <Container className={`media-default-skin media-default-skin--video ${className ?? ''}`} {...rest}>
        {isHlsUrl(src) ? (
          <HlsVideo src={src} playsInline autoPlay />
        ) : (
          <Video src={src} playsInline autoPlay />
        )}

        {poster ? (
          <Poster src={isString(poster) ? poster : undefined} render={isRenderProp(poster) ? poster : undefined} />
        ) : null}

        <BufferingIndicator
          render={(props) => (
            <div {...props} className="media-buffering-indicator">
              <div className="media-surface">
                <SpinnerIcon className="media-icon" />
              </div>
            </div>
          )}
        />

        <ErrorDialog.Root>
          <ErrorDialog.Popup className="media-error">
            <div className="media-error__dialog media-surface">
              <div className="media-error__content">
                <ErrorDialog.Title className="media-error__title">Something went wrong.</ErrorDialog.Title>
                <ErrorDialog.Description className="media-error__description" />
              </div>
              <div className="media-error__actions">
                <ErrorDialog.Close className="media-button media-button--primary">OK</ErrorDialog.Close>
              </div>
            </div>
          </ErrorDialog.Popup>
        </ErrorDialog.Root>

        <Controls.Root className="media-surface media-controls">
          <Tooltip.Provider>
            <div className="media-button-group">
              <Tooltip.Root side="top">
                <Tooltip.Trigger
                  render={
                    <PlayButton className="media-button--play" render={<Button />}>
                      <RestartIcon className="media-icon media-icon--restart" />
                      <PlayIcon className="media-icon media-icon--play" />
                      <PauseIcon className="media-icon media-icon--pause" />
                    </PlayButton>
                  }
                />
                <Tooltip.Popup className="media-surface media-tooltip" />
              </Tooltip.Root>

              <Tooltip.Root side="top">
                <Tooltip.Trigger
                  render={
                    <SeekButton seconds={-SEEK_TIME} className="media-button--seek" render={<Button />}>
                      <span className="media-icon__container">
                        <SeekIcon className="media-icon media-icon--seek media-icon--flipped" />
                        <span className="media-icon__label">{SEEK_TIME}</span>
                      </span>
                    </SeekButton>
                  }
                />
                <Tooltip.Popup className="media-surface media-tooltip" />
              </Tooltip.Root>

              <Tooltip.Root side="top">
                <Tooltip.Trigger
                  render={
                    <SeekButton seconds={SEEK_TIME} className="media-button--seek" render={<Button />}>
                      <span className="media-icon__container">
                        <SeekIcon className="media-icon media-icon--seek" />
                        <span className="media-icon__label">{SEEK_TIME}</span>
                      </span>
                    </SeekButton>
                  }
                />
                <Tooltip.Popup className="media-surface media-tooltip" />
              </Tooltip.Root>
            </div>

            <div className="media-time-controls">
              <Time.Value type="current" className="media-time" />
              <TimeSlider.Root className="media-slider">
                <TimeSlider.Track className="media-slider__track">
                  <TimeSlider.Fill className="media-slider__fill" />
                  <TimeSlider.Buffer className="media-slider__buffer" />
                </TimeSlider.Track>
                <TimeSlider.Thumb className="media-slider__thumb" />
                <div className="media-surface media-preview media-slider__preview">
                  <Slider.Thumbnail className="media-preview__thumbnail" />
                  <TimeSlider.Value type="pointer" className="media-time media-preview__time" />
                  <SpinnerIcon className="media-preview__spinner media-icon" />
                </div>
              </TimeSlider.Root>
              <Time.Value type="duration" className="media-time" />
            </div>

            <div className="media-button-group">
              <PlaybackRateMenu.Root side="top" align="center">
                <PlaybackRateMenu.Trigger className="media-button--playback-rate" render={<Button />} />
                <PlaybackRateMenu.Content className="media-surface media-popover media-menu media-menu--playback-rate">
                  <PlaybackRateMenuItems />
                </PlaybackRateMenu.Content>
              </PlaybackRateMenu.Root>

              <VolumePopover />

              <Tooltip.Root side="top">
                <Tooltip.Trigger
                  render={
                    <CaptionsButton className="media-button--captions" render={<Button />}>
                      <CaptionsOffIcon className="media-icon media-icon--captions-off" />
                      <CaptionsOnIcon className="media-icon media-icon--captions-on" />
                    </CaptionsButton>
                  }
                />
                <Tooltip.Popup className="media-surface media-tooltip" />
              </Tooltip.Root>

              <Tooltip.Root side="top">
                <Tooltip.Trigger
                  render={
                    <CastButton className="media-button--cast" render={<Button />}>
                      <CastEnterIcon className="media-icon media-icon--cast-enter" />
                      <CastExitIcon className="media-icon media-icon--cast-exit" />
                    </CastButton>
                  }
                />
                <Tooltip.Popup className="media-surface media-tooltip" />
              </Tooltip.Root>

              <Tooltip.Root side="top">
                <Tooltip.Trigger
                  render={
                    <PiPButton className="media-button--pip" render={<Button />}>
                      <PipEnterIcon className="media-icon media-icon--pip-enter" />
                      <PipExitIcon className="media-icon media-icon--pip-exit" />
                    </PiPButton>
                  }
                />
                <Tooltip.Popup className="media-surface media-tooltip" />
              </Tooltip.Root>

              <Tooltip.Root side="top">
                <Tooltip.Trigger
                  render={
                    <FullscreenButton className="media-button--fullscreen" render={<Button />}>
                      <FullscreenEnterIcon className="media-icon media-icon--fullscreen-enter" />
                      <FullscreenExitIcon className="media-icon media-icon--fullscreen-exit" />
                    </FullscreenButton>
                  }
                />
                <Tooltip.Popup className="media-surface media-tooltip" />
              </Tooltip.Root>
            </div>
          </Tooltip.Provider>
        </Controls.Root>

        <div className="media-overlay" />

        <Hotkey keys="Space" action="togglePaused" />
        <Hotkey keys="k" action="togglePaused" />
        <Hotkey keys="m" action="toggleMuted" />
        <Hotkey keys="f" action="toggleFullscreen" />
        <Hotkey keys="c" action="toggleSubtitles" />
        <Hotkey keys="i" action="togglePictureInPicture" />
        <Hotkey keys="ArrowRight" action="seekStep" value={SEEK_TIME / 2} />
        <Hotkey keys="ArrowLeft" action="seekStep" value={-(SEEK_TIME / 2)} />
        <Hotkey keys="l" action="seekStep" value={SEEK_TIME} />
        <Hotkey keys="j" action="seekStep" value={-SEEK_TIME} />
        <Hotkey keys="ArrowUp" action="volumeStep" value={0.05} />
        <Hotkey keys="ArrowDown" action="volumeStep" value={-0.05} />
        <Hotkey keys="0-9" action="seekToPercent" />
        <Hotkey keys="Home" action="seekToPercent" value={0} />
        <Hotkey keys="End" action="seekToPercent" value={100} />
        <Hotkey keys=">" action="speedUp" />
        <Hotkey keys="<" action="speedDown" />

        <Gesture type="tap" action="togglePaused" pointer="mouse" region="center" />
        <Gesture type="tap" action="toggleControls" pointer="touch" />
        <Gesture type="doubletap" action="seekStep" value={-SEEK_TIME} region="left" />
        <Gesture type="doubletap" action="toggleFullscreen" region="center" />
        <Gesture type="doubletap" action="seekStep" value={SEEK_TIME} region="right" />

        <StatusAnnouncer />
        <div className="media-input-feedback">
          <VolumeIndicator.Root className="media-surface media-input-feedback-island media-input-feedback-island--volume">
            <VolumeIndicator.Fill className="media-input-feedback-island__content">
              <VolumeHighIcon className="media-icon media-icon--volume-high" />
              <VolumeLowIcon className="media-icon media-icon--volume-low" />
              <VolumeOffIcon className="media-icon media-icon--volume-off" />
              <VolumeIndicator.Value className="media-input-feedback-island__value" />
            </VolumeIndicator.Fill>
          </VolumeIndicator.Root>

          <StatusIndicator.Root
            actions={TOP_STATUS_ACTIONS}
            className="media-surface media-input-feedback-island media-input-feedback-island--status"
          >
            <div className="media-input-feedback-island__content">
              <CaptionsOnIcon className="media-icon media-icon--captions-on" />
              <CaptionsOffIcon className="media-icon media-icon--captions-off" />
              <FullscreenEnterIcon className="media-icon media-icon--fullscreen-enter" />
              <FullscreenExitIcon className="media-icon media-icon--fullscreen-exit" />
              <PipEnterIcon className="media-icon media-icon--pip-enter" />
              <PipExitIcon className="media-icon media-icon--pip-exit" />
              <StatusIndicator.Value className="media-input-feedback-island__value" />
            </div>
          </StatusIndicator.Root>

          <SeekIndicator.Root className="media-input-feedback-bubble">
            <ChevronIcon className="media-icon media-icon--seek" />
            <SeekIndicator.Value className="media-time" />
          </SeekIndicator.Root>

          <StatusIndicator.Root actions={CENTER_STATUS_ACTIONS} className="media-input-feedback-bubble">
            <PlayIcon className="media-icon media-icon--play" />
            <PauseIcon className="media-icon media-icon--pause" />
          </StatusIndicator.Root>
        </div>
      </Container>
    </Player.Provider>
  );
}

const Button = forwardRef<HTMLButtonElement, ComponentProps<'button'>>(function Button(
  { className, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      className={`media-button media-button--subtle media-button--icon ${className ?? ''}`}
      {...props}
    />
  );
});

function VolumePopover(): ReactNode {
  const volumeUnsupported = usePlayer((s) => s.volumeAvailability === 'unsupported');

  const muteButton = (
    <MuteButton className="media-button--mute" render={<Button />}>
      <VolumeOffIcon className="media-icon media-icon--volume-off" />
      <VolumeLowIcon className="media-icon media-icon--volume-low" />
      <VolumeHighIcon className="media-icon media-icon--volume-high" />
    </MuteButton>
  );

  if (volumeUnsupported) {
    return muteButton;
  }

  return (
    <Popover.Root openOnHover delay={200} closeDelay={100} side="top">
      <Popover.Trigger render={muteButton} />
      <Popover.Popup className="media-surface media-popover media-popover--volume">
        <VolumeSlider.Root className="media-slider" orientation="vertical" thumbAlignment="edge">
          <VolumeSlider.Track className="media-slider__track">
            <VolumeSlider.Fill className="media-slider__fill" />
          </VolumeSlider.Track>
          <VolumeSlider.Thumb className="media-slider__thumb media-slider__thumb--persistent" />
        </VolumeSlider.Root>
      </Popover.Popup>
    </Popover.Root>
  );
}

function isString(value: unknown): value is string {
  return typeof value === 'string';
}

function isRenderProp(value: unknown): value is RenderProp<unknown> {
  return typeof value === 'function' || isValidElement(value);
}

export interface VideoPlayerProps {
  streamUrl: string;
  title: string;
  poster?: string;
  onError?: (message: string) => void;
  onPlaying?: () => void;
}

export function VideoPlayer({ streamUrl, title, poster, onError, onPlaying }: VideoPlayerProps) {
  return (
    <div className="player-aspect" aria-label={title}>
      <MediaSkinPlayer
        src={streamUrl}
        poster={poster}
        onError={onError}
        onPlaying={onPlaying}
        className="livetv-media-player"
      />
    </div>
  );
}
