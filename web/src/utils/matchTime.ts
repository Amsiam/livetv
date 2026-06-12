const startFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
});

const timeFormatter = new Intl.DateTimeFormat(undefined, {
  hour: 'numeric',
  minute: '2-digit',
});

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
});

function parseUtc(iso: string): Date {
  return new Date(iso);
}

/** Local start time, e.g. "Jun 9, 6:00 PM" */
export function formatMatchStart(iso: string): string {
  return startFormatter.format(parseUtc(iso));
}

/** Local date only */
export function formatMatchDate(iso: string): string {
  return dateFormatter.format(parseUtc(iso));
}

/** Local time only */
export function formatMatchTime(iso: string): string {
  return timeFormatter.format(parseUtc(iso));
}

/** Local range on one line for cards and detail */
export function formatMatchSchedule(startsAt: string, endsAt: string): string {
  const start = parseUtc(startsAt);
  const end = parseUtc(endsAt);
  const sameDay = start.toDateString() === end.toDateString();

  if (sameDay) {
    return `${formatMatchDate(startsAt)} · ${formatMatchTime(startsAt)} – ${formatMatchTime(endsAt)}`;
  }

  return `${formatMatchStart(startsAt)} – ${formatMatchStart(endsAt)}`;
}

export function formatMatchCardTime(
  status: 'scheduled' | 'live' | 'ended',
  startsAt: string,
  _endsAt: string,
): string {
  if (status === 'live') {
    return `Live · started ${formatMatchTime(startsAt)}`;
  }
  if (status === 'ended') {
    return `Ended · ${formatMatchStart(startsAt)}`;
  }
  return formatMatchStart(startsAt);
}
