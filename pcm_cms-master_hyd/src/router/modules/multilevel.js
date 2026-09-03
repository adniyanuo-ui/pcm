import Layout from '@/layout'
// import EmptyLayout from '@/layout/empty'

export default {
    path: '/patient',
    component: Layout,
    // redirect: '/patient/page',
    name: 'patient',
    meta: {
        title: '患者管理'
    },
    children: [
        {
            path: 'list',
            name: 'patient1',
            component: () => import(/* webpackChunkName: 'multilevel_menu_example' */ '@/views/patient/list.vue'),
            meta: {
                title: '患者管理'
            }
        }
    ],
}
