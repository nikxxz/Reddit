export function providerDisplayName(provider) {
  return {
    reddit: "Reddit",
    tumblr: "Tumblr",
    pinterest: "Pinterest",
    instagram: "Instagram"
  }[provider] || provider;
}

