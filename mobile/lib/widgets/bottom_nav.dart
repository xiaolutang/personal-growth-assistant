import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../config/app_routes.dart';
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
                this.context.go(AppRoutes.review);
              },
            ),
            ListTile(
              leading: const Icon(Icons.flag),
              title: const Text('目标'),
              onTap: () {
                Navigator.pop(context);
                this.context.go(AppRoutes.goals);
              },
            ),
            ListTile(
              leading: const Icon(Icons.settings),
              title: const Text('设置'),
              onTap: () {
                Navigator.pop(context);
                this.context.push(AppRoutes.settings);
              },
            ),
          ],
        ),
      ),
    );
  }

  int _currentIndex(String location) {
    if (location.startsWith(AppRoutes.chat)) return 1;
    if (location.startsWith(AppRoutes.tasks)) return 2;
    if (location.startsWith(AppRoutes.explore) ||
        location.startsWith(AppRoutes.notes) ||
        location.startsWith(AppRoutes.inbox)) {
      return 3;
    }
    return 0; // default: today
  }

  bool _isOnMoreRoute(String location) {
    return location.startsWith(AppRoutes.review) ||
        location.startsWith(AppRoutes.goals) ||
        location.startsWith(AppRoutes.settings);
  }

  /// 判断当前路由是否应该显示 FAB
  /// 全局唯一 FAB，仅条目详情页和目标详情页隐藏
  bool _shouldShowFab(String location) {
    if (AppRoutes.isEntryDetail(location)) return false;
    if (AppRoutes.isGoalDetail(location)) return false;
    return true;
  }

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).uri.path;
    final showFab = _shouldShowFab(location);

    return Stack(
      children: [
        Scaffold(
          body: widget.child,
          bottomNavigationBar: NavigationBar(
            selectedIndex: _isOnMoreRoute(location) ? 4 : _currentIndex(location),
            onDestinationSelected: (index) {
              if (index == 4) {
                _showMoreMenu();
                return;
              }
              switch (index) {
                case 0:
                  context.go(AppRoutes.today);
                case 1:
                  context.go(AppRoutes.chat);
                case 2:
                  context.go(AppRoutes.tasks);
                case 3:
                  context.go(AppRoutes.explore);
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
                label: '对话',
              ),
              NavigationDestination(
                icon: Icon(Icons.check_circle_outline),
                selectedIcon: Icon(Icons.check_circle),
                label: '任务',
              ),
              NavigationDestination(
                icon: Icon(Icons.explore_outlined),
                selectedIcon: Icon(Icons.explore),
                label: '探索',
              ),
              NavigationDestination(
                icon: Icon(Icons.person_outline),
                selectedIcon: Icon(Icons.person),
                label: '我的',
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
