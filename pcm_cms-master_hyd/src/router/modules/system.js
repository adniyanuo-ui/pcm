import Layout from '@/layout'
// import EmptyLayout from '@/layout/empty'

export default {
    path: '/system',
    component: Layout,
    // redirect: '/patient/page',
    name: 'system',
    meta: {
        title: '系统管理'
    },
    children: [
        {
            path: 'list',
            name: 'qr',
            component: () => import(/* webpackChunkName: 'multilevel_menu_example' */ '@/views/qr/list.vue'),
            meta: {
                title: '二维码管理'
            }
        }
    ],
}
