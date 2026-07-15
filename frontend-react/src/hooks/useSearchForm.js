import { useMemo, useState } from "react";

const INITIAL_VALUES = {
  query: "",
  subreddit: "",
  mediaType: "all",
  sortBy: "relevance",
  timeFilter: "all",
  includeNsfw: false,
  validationError: ""
};

export function useSearchForm() {
  const [values, setValues] = useState(INITIAL_VALUES);
  const [submittedValues, setSubmittedValues] = useState(null);

  const setFieldValue = (field, value) => {
    setValues((current) => ({
      ...current,
      [field]: value,
      validationError: field === "query" || field === "subreddit"
        ? ""
        : current.validationError
    }));
  };

  const submitSearch = (event) => {
    event.preventDefault();

    const query = values.query.trim();
    const subreddit = values.subreddit.trim().replace(/^r\//i, "");

    if (!query && !subreddit) {
      setValues((current) => ({
        ...current,
        validationError: "Enter a keyword or subreddit."
      }));
      return;
    }

    const nextSubmittedValues = {
      ...values,
      query,
      subreddit,
      validationError: ""
    };

    setValues(nextSubmittedValues);
    setSubmittedValues(nextSubmittedValues);
  };

  const summaryValues = useMemo(
    () => submittedValues && {
      ...submittedValues,
      mediaType: values.mediaType,
      sortBy: values.sortBy,
      timeFilter: values.timeFilter,
      includeNsfw: values.includeNsfw
    },
    [submittedValues, values.mediaType, values.sortBy, values.timeFilter, values.includeNsfw]
  );

  return {
    values,
    submittedValues: summaryValues,
    setFieldValue,
    submitSearch
  };
}
