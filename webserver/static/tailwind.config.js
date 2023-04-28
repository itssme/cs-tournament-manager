module.exports = {
    content: ['/app/templates/**/*.html', './node_modules/tw-elements/dist/js/**/*.js'],
    darkMode: 'media',
    variants: {extend: {},},
    plugins: [require('tw-elements/dist/plugin')],
    theme: {
        extend: {
            colors: {
                'profile-blue': '#60a5fa',
                'profile-red': '#f43f5e',
                'profile-green': '#22c55e',
                'profile-teal': '#0d9488',
                'profile-orange': '#fdba74',
            }
        }

    },
    safelist: [
        'bg-profile-blue',
        'bg-profile-red',
        'bg-profile-green',
        'bg-profile-teal',
        'bg-profile-orange'
    ]
}