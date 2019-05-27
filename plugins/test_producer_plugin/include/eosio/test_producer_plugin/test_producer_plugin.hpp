/**
 *  @file
 *  @copyright defined in eos/LICENSE.txt
 */
#pragma once
#include <appbase/application.hpp>
#include <eosio/chain/controller.hpp>
#include <eosio/producer_plugin/producer_plugin.hpp>

namespace eosio {

  using std::unique_ptr;
  using chain::controller;

  using namespace appbase;

namespace test_producer_apis
{

  class read_write
  {
    public:

      /**
       * This structure holds length of time, which will generate shift in blockchain timeline.
       */

      struct accelerate_time_params
      {
        uint32_t time;
        std::string type;
      };

      using accelerate_mock_time_params = accelerate_time_params;
     /**
      * RPC request example:

        curl --url http://127.0.0.1:8888/v1/test_producer/accelerate_time --data
         '{
            "time":1,
            "type":"m"
          }
          '
     */

      /**
       * This structure holds number of blocks, which will be skipped.
       */

      struct accelerate_blocks_params
      {
        uint32_t blocks;
      };

     /**
      * RPC request example:

        curl --url http://127.0.0.1:8888/v1/test_producer/accelerate_blocks --data
         '{
            "blocks":1
          }
          '
     */

      /**
       * This structure holds information if acceleration was done.
       */

      struct accelerate_results
      {
        bool done;
        accelerate_results(bool _done ) : done(_done)
        {
        }
      };


    private:

      producer_plugin* producer_plug = nullptr;

      template< typename CallMethod >
      accelerate_results accelerate_time_internal( const accelerate_time_params& params, CallMethod method );

    public:

      read_write( producer_plugin* _producer_plug )
          : producer_plug( _producer_plug ) {}


      accelerate_results accelerate_time( const accelerate_time_params& params );
      accelerate_results accelerate_mock_time( const accelerate_time_params& params );
      accelerate_results accelerate_blocks( const accelerate_blocks_params& params );
  };

} // namespace chain_apis

class test_producer_plugin : public plugin<test_producer_plugin>
{
   public:

      APPBASE_PLUGIN_REQUIRES((test_producer_plugin))

      test_producer_plugin();
      virtual ~test_producer_plugin();

      virtual void set_program_options(options_description& cli, options_description& cfg) override;

      void plugin_initialize(const variables_map& options);
      void plugin_startup();
      void plugin_shutdown();

      test_producer_apis::read_write get_read_write_api() const;

   private:

    unique_ptr<class test_producer_plugin_impl> my;
};

} /// namespace eosio

FC_REFLECT( eosio::test_producer_apis::read_write::accelerate_time_params, (time)(type))
FC_REFLECT( eosio::test_producer_apis::read_write::accelerate_blocks_params, (blocks))
FC_REFLECT( eosio::test_producer_apis::read_write::accelerate_results, (done) )
