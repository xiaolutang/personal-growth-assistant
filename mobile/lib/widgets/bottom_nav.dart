import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/command_result.dart';
import '../providers/command_bar_provider.dart';
import '../providers/today_provider.dart';
import 'draggable_fab.dart';
import 'quick_capture_fab.dart';

class BottomNavShell extends ConsumerStatefulWidget {
  final Widget child;

  const BottomNavShell({super.key, required this.child});

  @override
  ConsumerState<BottomNavShell> createState() => _BottomNavShellState();
}

class _BottomNavShellState extends ConsumerState<BottomNavShell> {
  /// FAB 展开状态，由 QuickCaptureFAB 回调更新
  bool _isFabExpanded = false;

  /// FAB 的 GlobalKey，用于屏障层点击时通知 FAB 收起
  final _fabKey = GlobalKey<QuickCaptureFABState>();

  void _showMoreMenu() {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Wrap(
          children: [
            ListTile(
              leading: const Icon(Icons.bar_chart),
              title: const Text('回顾'),
              onTap: () {
                Navigator.pop(context);
                this.context.go('/review');
              },
            ),
            ListTile(
              leading: const Icon(Icons.flag),
              title: const Text('目标'),
              onTap: () {
                Navigator.pop(context);
                this.context.go('/goals');
              },
            ),
            ListTile(
              leading: const Icon(Icons.lightbulb),
              title: const Text('灵感'),
              onTap: () {
                Navigator.pop(context);
                this.context.go('/inbox');
              },
            ),
            ListTile(
              leading: const Icon(Icons.explore),
              title: const Text('探索'),
              onTap: () {
                Navigator.pop(context);
                this.context.go('/explore');
              },
            ),
            ListTile(
              leading: const Icon(Icons.chat_bubble),
              title: const Text('对话'),
              onTap: () {
                Navigator.pop(context);
                this.context.go('/chat');
              },
            ),
            ListTile(
              leading: const Icon(Icons.settings),
              title: const Text('设置'),
              onTap: () {
                Navigator.pop(context);
                this.context.push('/settings');
              },
            ),
          ],
        ),
      ),
    );
  }

  int _currentIndex() {
    final location = GoRouterState.of(context).uri.path;
    if (location.startsWith('/chat')) return 1;
    if (location.startsWith('/tasks')) return 2;
    if (location.startsWith('/notes')) return 3;
    return 0; // default: today
  }

  bool _isOnMoreRoute() {
    final location = GoRouterState.of(context).uri.path;
    return location.startsWith('/review') ||
        location.startsWith('/goals') ||
        location.startsWith('/inbox') ||
        location.startsWith('/explore');
  }

  /// 判断当前路由是否应该显示 FAB
  /// 全局唯一 FAB，仅条目详情页和目标详情页隐藏
  bool _shouldShowFab() {
    final location = GoRouterState.of(context).uri.path;
    if (location.startsWith('/entries/')) return false;
    if (RegExp(r'^/goals/[^/]+$').hasMatch(location)) return false;
    return true;
  }

  /// 判断当前是否在 Today 页面（Today 页面有自己的 commandBar 结果展示）
  bool _isOnTodayPage() {
    final location = GoRouterState.of(context).uri.path;
    return location == '/';
  }

  /// 全局监听 commandBarProvider 结果变化，在非 Today 页面提供 SnackBar 反馈
  void _onCommandResultChanged(CommandBarState? previous, CommandBarState next) {
    final prevResult = previous?.result;
    final nextResult = next.result;

    // 只在 result 变化时触发
    if (nextResult == null || nextResult == prevResult) return;
    if (previous?.isLoading == true && next.isLoading) return;

    // Today 页面有自己的内联展示，不需要全局 SnackBar
    if (_isOnTodayPage()) return;

    switch (nextResult.type) {
      case CommandResultType.success:
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(nextResult.message),
            duration: const Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
          ),
        );
        // success 后刷新 today 数据（因为可能创建了新条目）
        ref.read(todayProvider.notifier).loadData();
      case CommandResultType.error:
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(nextResult.message),
            duration: const Duration(seconds: 3),
            behavior: SnackBarBehavior.floating,
          ),
        );
      case CommandResultType.answer:
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(nextResult.answer ?? nextResult.message),
            duration: const Duration(seconds: 4),
            behavior: SnackBarBehavior.floating,
          ),
        );
      case CommandResultType.redirectChat:
        // redirect 类型：提示用户跳转
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('已转至日知对话'),
            duration: const Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
            action: SnackBarAction(
              label: '前往',
              onPressed: () {
                ref.read(commandBarProvider.notifier).clearResult();
                context.go('/chat');
              },
            ),
          ),
        );
    }
  }

  @override
  Widget build(BuildContext context) {
    final showFab = _shouldShowFab();

    // 监听 commandBarProvider 结果变化
    ref.listen(commandBarProvider, (previous, next) {
      _onCommandResultChanged(previous, next);
    });

    return Stack(
      children: [
        Scaffold(
          body: widget.child,
          bottomNavigationBar: NavigationBar(
            selectedIndex: _isOnMoreRoute() ? 4 : _currentIndex(),
            onDestinationSelected: (index) {
              if (index == 4) {
                _showMoreMenu();
                return;
              }
              switch (index) {
                case 0:
                  context.go('/');
                case 1:
                  context.go('/chat');
                case 2:
                  context.go('/tasks');
                case 3:
                  context.go('/notes');
              }
            },
            destinations: const [
              NavigationDestination(
                icon: Icon(Icons.home_outlined),
                selectedIcon: Icon(Icons.home),
                label: '今天',
              ),
              NavigationDestination(
                icon: Icon(Icons.chat_bubble_outline),
                selectedIcon: Icon(Icons.chat_bubble),
                label: '日知',
              ),
              NavigationDestination(
                icon: Icon(Icons.check_circle_outline),
                selectedIcon: Icon(Icons.check_circle),
                label: '任务',
              ),
              NavigationDestination(
                icon: Icon(Icons.note_outlined),
                selectedIcon: Icon(Icons.note),
                label: '笔记',
              ),
              NavigationDestination(
                icon: Icon(Icons.more_horiz),
                selectedIcon: Icon(Icons.more_horiz),
                label: '更多',
              ),
            ],
          ),
        ),
        // FAB 展开时的透明屏障层：点击空白区域收起 FAB
        if (showFab && _isFabExpanded)
          Positioned.fill(
            child: GestureDetector(
              onTap: () {
                _fabKey.currentState?.collapse();
                setState(() => _isFabExpanded = false);
              },
              behavior: HitTestBehavior.opaque,
              child: const SizedBox.expand(),
            ),
          ),
        // 全局 FAB
        if (showFab)
          DraggableFAB(
            child: QuickCaptureFAB(
              key: _fabKey,
              onExpandChanged: (expanded) {
                setState(() => _isFabExpanded = expanded);
              },
            ),
          ),
      ],
    );
  }
}
