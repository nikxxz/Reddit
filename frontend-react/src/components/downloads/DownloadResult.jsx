import { List, Text } from "@mantine/core";

export function DownloadResult({ files }) {
  if (!files?.length) {
    return null;
  }

  return (
    <List spacing={4} size="sm">
      {files.map((file, index) => (
        <List.Item key={`${file.filename || "file"}-${index}`}>
          <Text span fw={600}>
            {file.filename || "Media file"}
          </Text>
          {file.status === "failed" ? (
            <Text span c="red.7">
              {" "}
              - {file.error || "failed"}
            </Text>
          ) : null}
        </List.Item>
      ))}
    </List>
  );
}
