const dateFormatter = new Intl.DateTimeFormat(undefined, {
  day: "2-digit",
  month: "short",
  year: "numeric",
});


export function formatRedditDate(item) {
  if (item.createdAt) {
    return item.createdAt;
  }
  if (!item.created_utc) {
    return "";
  }
  return dateFormatter.format(new Date(item.created_utc * 1000));
}
