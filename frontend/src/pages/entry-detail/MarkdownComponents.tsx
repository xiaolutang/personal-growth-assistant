/** 共享的 Markdown 链接渲染器：/entries/ 走 SPA 导航，其他走原生跳转 */
export function getMarkdownComponents(navigate: (path: string) => void) {
  return {
    a: ({ href, children }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { children?: React.ReactNode }) => {
      if (href?.startsWith("/entries/")) {
        return (
          <span
            className="text-primary hover:underline cursor-pointer"
            onClick={() => navigate(href)}
          >
            {children}
          </span>
        );
      }
      return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
    },
  };
}
